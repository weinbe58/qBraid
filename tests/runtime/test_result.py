# Copyright (C) 2024 qBraid
#
# This file is part of the qBraid-SDK
#
# The qBraid-SDK is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for the qBraid-SDK, as per Section 15 of the GPL v3.

# pylint: disable=redefined-outer-name

"""
Unit tests for retrieving and post-processing experimental results.

"""
import datetime
from collections import Counter
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from qbraid.programs import ExperimentType
from qbraid.runtime.native.result import (
    NECVectorAnnealerResultData,
    QbraidQirSimulatorResultData,
    QuEraQasmSimulatorResultData,
)
from qbraid.runtime.postprocess import (
    format_counts,
    normalize_batch_bit_lengths,
    normalize_bit_lengths,
    normalize_counts,
)
from qbraid.runtime.result import (
    AhsResultData,
    AhsShotResult,
    AnnealingResultData,
    GateModelResultData,
    Result,
)

try:
    from flair_visual.animation.runtime.qpustate import AnimateQPUState

    flair_visual_installed = True
except ImportError:
    flair_visual_installed = False


@pytest.fixture
def annealing_result_data() -> AnnealingResultData:
    """Fixture to create an AnnealingResultData object with some test data.
    Returns:
        AnnealingResultData: An AnnealingResultData object.
    """
    return AnnealingResultData(
        solutions=[
            {
                "spin": {" x1": 0, " x2": 0, "x1": 0},
                "energy": 0,
                "time": 0.006517000030726194,
                "constraint": True,
                "memory_usage": 1.189453125,
            }
        ]
    )


@pytest.fixture
def nec_vector_annealer_result_data() -> NECVectorAnnealerResultData:
    """Fixture to create an NECVectorAnnealerResultData object with some test data.
    Returns:
        NECVectorAnnealerResultData: An NECVectorAnnealerResultData object.
    """
    return NECVectorAnnealerResultData(
        [
            {
                "spin": {" x1": 0, " x2": 0, "x1": 0},
                "energy": 0,
                "time": 0.006517000030726194,
                "constraint": True,
                "memory_usage": 1.189453125,
            }
        ]
    )


@pytest.fixture
def gate_model_result_data():
    """Fixture to create a GateModelResultData object with some test data."""
    measurement_counts = {"00": 100, "01": 50, "10": 25}
    measurements = np.array([[0, 0], [0, 1], [1, 0]])
    return GateModelResultData(measurement_counts=measurement_counts, measurements=measurements)


@pytest.fixture
def shot_result() -> AhsShotResult:
    """Fixture to create an AhsShotResult object."""
    success = True
    pre_sequence = np.array([1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1])
    post_sequence = np.array([0, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0])
    return AhsShotResult(success=success, pre_sequence=pre_sequence, post_sequence=post_sequence)


@pytest.fixture
def ahs_result_data(shot_result: AhsShotResult) -> AhsResultData:
    """Fixture to create an AhsResultData object."""
    measurements = [shot_result]
    state_counts = Counter()
    states = ["e", "r", "g"]

    for shot in measurements:
        if shot.success:
            pre = shot.pre_sequence
            post = shot.post_sequence
            state_idx = [
                0 if pre_i == 0 else 1 if post_i == 0 else 2 for pre_i, post_i in zip(pre, post)
            ]
            state = "".join(states[s_idx] for s_idx in state_idx)
            state_counts.update([state])

    measurement_counts = dict(state_counts)
    return AhsResultData(measurement_counts=measurement_counts, measurements=measurements)


@pytest.fixture
def mock_atom_animation_state() -> dict[str, Any]:
    """Fixture for a mock AnimateQPUState JSON data."""
    return {
        "block_durations": [],
        "gate_events": [],
        "qpu_fov": {"xmin": None, "xmax": None, "ymin": None, "ymax": None},
        "atoms": [],
        "slm_zone": [],
        "aod_moves": [],
    }


@pytest.fixture
def mock_logs() -> list[dict[str, Any]]:
    """Fixture for mock logs."""
    return [
        {"atom_id": 0, "block_id": 0, "action_type": "TrapSLM", "time": 0, "duration": 0},
        {
            "atom_id": 0,
            "block_id": 0,
            "action_type": "TrapAOD",
            "time": 0,
            "duration": 31.024984394500784,
        },
        {
            "atom_id": 0,
            "block_id": 0,
            "action_type": "DropAOD",
            "time": 31.024984394500784,
            "duration": 0,
        },
    ]


@pytest.fixture
def quera_sim_data(mock_atom_animation_state, mock_logs) -> QuEraQasmSimulatorResultData:
    """Fixture to create a QuEraQasmSimulatorResultData object."""
    return QuEraQasmSimulatorResultData(
        backend="cirq",
        flair_visual_version="0.1.4",
        atom_animation_state=mock_atom_animation_state,
        logs=mock_logs,
    )


@pytest.fixture
def qir_sim_data():
    """Fixture to create a QbraidQirSimulatorResultData object."""
    return QbraidQirSimulatorResultData(
        backend_version="0.7.4",
        seed=42,
        measurement_counts={"00": 10, "01": 15},
    )


@pytest.fixture
def result_instance():
    """Fixture to create a Result object for testing."""
    return Result(
        device_id="test_device",
        job_id="test_job",
        success=True,
        data=GateModelResultData(),
        test_detail="test_value",
    )


@pytest.mark.parametrize(
    "counts_raw, expected_out, include_zero_values",
    [
        ({" 1": 0, "0": 550}, {"0": 550}, False),
        ({"10": 479, "1 1": 13, "0 0 ": 496}, {"00": 496, "10": 479, "11": 13}, False),
        ({" 1": 474, "0": 550}, {"0": 550, "1": 474}, True),
        ({"10": 479, "1 1": 13, "0 0 ": 496}, {"00": 496, "01": 0, "10": 479, "11": 13}, True),
        (
            {"10 1": 586, "11  0  ": 139, "0 01": 496, "  010": 543, "11 1": 594},
            {
                "000": 0,
                "001": 496,
                "010": 543,
                "011": 0,
                "100": 0,
                "101": 586,
                "110": 139,
                "111": 594,
            },
            True,
        ),
    ],
)
def test_format_counts(counts_raw, expected_out, include_zero_values):
    """Test formatting of raw measurement counts."""
    counts_out = format_counts(counts_raw, include_zero_values=include_zero_values)
    assert counts_out == expected_out  # check equivalance
    assert list(counts_out.items()) == list(expected_out.items())  # check ordering of keys


def test_normalize_different_key_lengths():
    """Test normalization of measurement counts with different key lengths."""
    measurements = [{"0": 10, "1": 15}, {"00": 5, "01": 8, "10": 12}]
    expected = [{"00": 10, "01": 15}, {"00": 5, "01": 8, "10": 12}]
    assert normalize_batch_bit_lengths(measurements) == expected


def test_normalize_same_key_lengths():
    """Test normalization of measurement counts with the same key lengths."""
    measurements = [{"00": 7, "01": 9}, {"10": 4, "11": 3}]
    expected = [{"00": 7, "01": 9}, {"10": 4, "11": 3}]
    assert normalize_batch_bit_lengths(measurements) == expected


def test_empty_input():
    """Test normalization of empty input."""
    measurements = []
    expected = []
    assert normalize_batch_bit_lengths(measurements) == expected


def test_empty_dicts():
    """Test normalization of empty dicts."""
    measurements = [{}, {}, {"00": 1, "11": 2}]
    expected = [{}, {}, {"00": 1, "11": 2}]
    assert normalize_batch_bit_lengths(measurements) == expected


def test_normalize_single_dict():
    """Test normalization of a single dict."""
    measurements = {"0": 2, "1": 3, "10": 4, "11": 1}
    expected = {"00": 2, "01": 3, "10": 4, "11": 1}
    assert normalize_bit_lengths(measurements) == expected


def test_get_counts_raises_for_no_measurements():
    """Test that an error is raised when no measurements are available."""
    data = GateModelResultData()
    with pytest.raises(ValueError) as excinfo:
        data.get_counts()
    assert str(excinfo.value) == "Counts data is not available."


def test_get_counts_from_cache_key():
    """Test that counts are retrieved from the cache key."""
    data = GateModelResultData(measurement_counts={"10": 2})
    assert all(value is None for value in data._cache.values())
    counts = data.get_counts()
    assert data._cache["bin_nz"] == counts
    data._cache["bin_nz"] = 42
    assert data.get_counts() == 42


class MockBatchResult:
    """Mock batch result for testing."""

    def get_counts(self):
        """Returns raw histogram data of the run."""
        return [{" 1": 0, "0": 550}, {" 1": 474, "0": 550}]


def test_batch_normalized_counts():
    """Test batch measurement counts."""
    result = MockBatchResult()
    raw_counts = result.get_counts()
    counts = normalize_counts(raw_counts, include_zero_values=False)
    expected = [{"0": 550}, {"0": 550, "1": 474}]
    assert counts == expected


def test_decimal_get_counts():
    """Test decimal raw counts."""
    experiment = GateModelResultData(measurement_counts={"10": 2})
    result = Result("device_id", "job_id", True, experiment)
    counts = result.data.get_counts(decimal=True)
    expected = {2: 2}
    assert counts == expected


def test_result_data_experiment_type():
    """Test that result data classes return the correct experiment type."""
    gm_result_data = GateModelResultData()
    ahs_result_data = AhsResultData()
    assert gm_result_data.experiment_type == ExperimentType.GATE_MODEL
    assert ahs_result_data.experiment_type == ExperimentType.AHS


def test_to_dict_basic(gate_model_result_data):
    """Test the basic functionality of the to_dict method."""
    result_dict = gate_model_result_data.to_dict()

    assert isinstance(result_dict, dict)
    assert result_dict["shots"] == 175
    assert result_dict["num_measured_qubits"] == 2
    assert result_dict["measurement_counts"] == {"00": 100, "01": 50, "10": 25}
    assert "measurement_probabilities" in result_dict
    assert np.array_equal(result_dict["measurements"], np.array([[0, 0], [0, 1], [1, 0]]))


def test_to_dict_cache(gate_model_result_data):
    """Test that the to_dict method uses caching correctly."""
    assert gate_model_result_data._cache["to_dict"] is None
    gate_model_result_data.to_dict()

    assert gate_model_result_data._cache["to_dict"] is not None

    cached_result = gate_model_result_data._cache["to_dict"]
    result_dict = gate_model_result_data.to_dict()

    assert result_dict == cached_result


def test_to_dict_with_empty_measurements():
    """Test the to_dict method when there are no measurements provided."""
    measurement_counts = {"00": 100, "01": 50}
    result_data = GateModelResultData(measurement_counts=measurement_counts, measurements=None)

    result_dict = result_data.to_dict()

    assert result_dict["measurements"] is None
    assert result_dict["measurement_counts"] == {"00": 100, "01": 50}
    assert result_dict["shots"] == 150
    assert result_dict["num_measured_qubits"] == 2


def test_to_dict_probabilities(gate_model_result_data):
    """Test that the probabilities are correctly included in the dictionary."""
    result_dict = gate_model_result_data.to_dict()
    probabilities = result_dict["measurement_probabilities"]
    assert abs(sum(probabilities.values()) - 1) < 1e-6


def test_get_probabilities_from_cache(gate_model_result_data):
    """Test that probabilities are retrieved from cache if present."""
    assert gate_model_result_data._cache["prob_dec_nz"] is None
    calculated_probs = gate_model_result_data.get_probabilities(decimal=True)
    assert gate_model_result_data._cache["prob_dec_nz"] == calculated_probs
    mock_cached_probs = {}
    assert mock_cached_probs != calculated_probs
    gate_model_result_data._cache["prob_dec_nz"] = mock_cached_probs
    retrieved_probs = gate_model_result_data.get_probabilities(decimal=True)
    assert retrieved_probs == mock_cached_probs


def test_to_dict_no_counts():
    """Test the to_dict method when measurement counts are not available."""
    result_data = GateModelResultData(measurement_counts=None, measurements=None)

    with pytest.raises(ValueError, match="Counts data is not available"):
        result_data.to_dict()


def test_ahs_shot_result_equality(shot_result):
    """Test equality of two AhsShotResult objects."""
    shot_result_2 = AhsShotResult(
        success=True,
        pre_sequence=np.array([1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1]),
        post_sequence=np.array([0, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0]),
    )

    assert shot_result == shot_result_2

    shot_result_3 = AhsShotResult(
        success=True,
        pre_sequence=np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]),
        post_sequence=np.array([0, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0]),
    )

    assert shot_result != shot_result_3
    assert shot_result != "not a shot result"


def test_ahs_shot_result_sequences_equal():
    """Test the _sequences_equal method."""
    seq1 = np.array([1, 1, 0])
    seq2 = np.array([1, 1, 0])

    assert AhsShotResult._sequences_equal(seq1, seq2)

    seq3 = np.array([0, 1, 0])
    assert not AhsShotResult._sequences_equal(seq1, seq3)
    assert AhsShotResult._sequences_equal(None, None)
    assert not AhsShotResult._sequences_equal(seq1, None)


def test_ahs_result_data_experiment_type(ahs_result_data):
    """Test that the experiment type is AHS."""
    assert ahs_result_data.experiment_type == ExperimentType.AHS


def test_ahs_result_data_measurements(ahs_result_data, shot_result):
    """Test the measurements property."""
    assert ahs_result_data.measurements == [shot_result]


def test_ahs_result_data_get_counts(ahs_result_data):
    """Test the get_counts method."""
    expected_counts = {"rrrgeggrrgr": 1}
    assert ahs_result_data.get_counts() == expected_counts


def test_ahs_result_data_to_dict(ahs_result_data):
    """Test the to_dict method of AhsResultData."""
    expected_dict = {
        "measurement_counts": {"rrrgeggrrgr": 1},
        "measurements": ahs_result_data.measurements,
    }

    assert ahs_result_data.to_dict() == expected_dict


def test_ahs_result_data_no_measurement_counts():
    """Test to_dict and get_counts when there are no measurement counts."""
    result_data = AhsResultData(measurement_counts=None, measurements=None)

    assert result_data.get_counts() is None

    expected_dict = {
        "measurement_counts": None,
        "measurements": None,
    }
    assert result_data.to_dict() == expected_dict


def test_quera_sim_data_properties(quera_sim_data: QuEraQasmSimulatorResultData):
    """Test the backend and flair_visual_version properties."""
    assert quera_sim_data.backend == "cirq"
    assert quera_sim_data.flair_visual_version == "0.1.4"


@pytest.mark.skipif(not flair_visual_installed, reason="flair-visual is not installed.")
def test_quera_sim_data_get_qpu_state(quera_sim_data: QuEraQasmSimulatorResultData):
    """Test that get_qpu_state returns an instance of AnimateQPUState."""
    state = quera_sim_data.get_qpu_state()
    assert isinstance(state, AnimateQPUState)


@pytest.mark.skipif(not flair_visual_installed, reason="flair-visual is not installed.")
@patch("flair_visual.animation.runtime.qpustate.AnimateQPUState.from_json")
def test_quera_sim_data_get_qpu_state_calls(
    mock_from_json, quera_sim_data, mock_atom_animation_state
):
    """Test that get_qpu_state uses from_json call to create AnimateQPUState."""
    mock_qpu_state = MagicMock()
    mock_from_json.return_value = mock_qpu_state

    state = quera_sim_data.get_qpu_state()

    mock_from_json.assert_called_once_with(mock_atom_animation_state)
    assert state == mock_qpu_state


@pytest.mark.skipif(not flair_visual_installed, reason="flair-visual is not installed.")
def test_quera_sim_data_get_qpu_state_raises_value_error():
    """Test that get_qpu_state raises ValueError if atom_animation_state is None."""
    result_data = QuEraQasmSimulatorResultData(
        backend="cirq",
        flair_visual_version="0.1.4",
        atom_animation_state=None,
        logs=[],
    )

    with pytest.raises(ValueError, match="No atom_animation_state found in the result data."):
        result_data.get_qpu_state()


def test_quera_sim_data_get_logs_as_dataframe(quera_sim_data: QuEraQasmSimulatorResultData):
    """Test that get_logs returns the logs as a pandas DataFrame."""
    result = quera_sim_data.get_logs()

    assert isinstance(result, pd.DataFrame)
    assert result.shape == (3, 5)  # 3 rows (3 log entries) and 5 columns
    assert list(result.columns) == ["atom_id", "block_id", "action_type", "time", "duration"]
    assert result["atom_id"].iloc[0] == 0
    assert result["block_id"].iloc[1] == 0
    assert result["action_type"].iloc[2] == "DropAOD"
    assert result["time"].iloc[2] == 31.024984394500784
    assert result["duration"].iloc[1] == 31.024984394500784


def test_quera_sim_data_get_logs_with_empty_logs():
    """Test that get_logs returns an empty DataFrame when there are no logs."""
    result_data = QuEraQasmSimulatorResultData(
        backend="cirq",
        flair_visual_version="0.1.4",
        atom_animation_state={},
        logs=[],
    )

    result = result_data.get_logs()

    assert isinstance(result, pd.DataFrame)
    assert result.empty


def test_qir_sim_data_backend_version_property(qir_sim_data):
    """Test the backend_version property."""
    assert qir_sim_data.backend_version == "0.7.4"


def test_qir_sim_data_seed_property_with_value(qir_sim_data):
    """Test the seed property when a seed is provided."""
    assert qir_sim_data.seed == 42


def test_qir_sim_data_seed_property_with_none():
    """Test the seed property when no seed is provided."""
    result_data = QbraidQirSimulatorResultData(
        backend_version="v1.2.3",
        seed=None,
        measurement_counts={"00": 10, "01": 15},
    )

    assert result_data.seed is None


def test_qir_sim_data_inherited_measurement_counts_property(qir_sim_data):
    """Test that the inherited measurement_counts property is working correctly."""
    assert qir_sim_data.get_counts() == {"00": 10, "01": 15}


def test_nec_vector_annealer_result_data(nec_vector_annealer_result_data):
    """Test NECVectorAnnealerResultData."""
    assert nec_vector_annealer_result_data._solutions == [
        {
            "spin": {" x1": 0, " x2": 0, "x1": 0},
            "energy": 0,
            "time": 0.006517000030726194,
            "constraint": True,
            "memory_usage": 1.189453125,
        }
    ]


def test_nec_vector_annealer_result_data_to_dict(nec_vector_annealer_result_data):
    """Test NECVectorAnnealerResultData to_dict."""
    result_dict = nec_vector_annealer_result_data.to_dict()
    assert result_dict == {
        "solutions": [
            {
                "spin": {" x1": 0, " x2": 0, "x1": 0},
                "energy": 0,
                "time": 0.006517000030726194,
                "constraint": True,
                "memory_usage": 1.189453125,
            }
        ],
        "num_solutions": 1,
    }


def test_nec_vector_annealer_result_data_eq(nec_vector_annealer_result_data):
    """Test NECVectorAnnealerResultData equality."""
    assert nec_vector_annealer_result_data._solutions[0]["spin"] == {" x1": 0, " x2": 0, "x1": 0}
    assert nec_vector_annealer_result_data._solutions[0]["energy"] == 0
    assert nec_vector_annealer_result_data._solutions[0]["time"] == 0.006517000030726194
    assert nec_vector_annealer_result_data._solutions[0]["constraint"] is True
    assert nec_vector_annealer_result_data._solutions[0]["memory_usage"] == 1.189453125


def test_annealing_result_data(annealing_result_data):
    """Test AnnealingResultData."""
    assert annealing_result_data._solutions == [
        {
            "spin": {" x1": 0, " x2": 0, "x1": 0},
            "energy": 0,
            "time": 0.006517000030726194,
            "constraint": True,
            "memory_usage": 1.189453125,
        }
    ]


def test_annealing_result_from_dict():
    """Test AnnealingResultData from_dict."""
    solutions = [
        {
            "spin": {" x1": 0, " x2": 0, "x1": 0},
            "energy": 0,
            "time": 0.006517000030726194,
            "constraint": True,
            "memory_usage": 1.189453125,
        }
    ]
    result_data = AnnealingResultData.from_dict({"solutions": solutions})
    assert result_data._solutions == solutions


def test_annealing_result_data_get_result(annealing_result_data):
    """Test AnnealingResultData get_result."""
    result = annealing_result_data.solutions
    assert result == [
        {
            "spin": {" x1": 0, " x2": 0, "x1": 0},
            "energy": 0,
            "time": 0.006517000030726194,
            "constraint": True,
            "memory_usage": 1.189453125,
        }
    ]


def test_annealing_result_data_get_result_with_empty_solutions():
    """Test AnnealingResultData get_result with empty solutions."""
    result_data = AnnealingResultData(solutions=None)
    assert result_data.solutions is None


def test_annealing_result_data_get_result_experiment_type(annealing_result_data):
    """Test AnnealingResultData get_result experiment type."""
    assert annealing_result_data.experiment_type == ExperimentType.ANNEALING


def test_annealing_result_data_to_dict(annealing_result_data):
    """Test AnnealingResultData to_dict."""
    result_dict = annealing_result_data.to_dict()
    assert result_dict == {
        "solutions": [
            {
                "spin": {" x1": 0, " x2": 0, "x1": 0},
                "energy": 0,
                "time": 0.006517000030726194,
                "constraint": True,
                "memory_usage": 1.189453125,
            }
        ],
        "num_solutions": 1,
    }


def test_normalize_batch_decimal_counts():
    """Test normalization of batch measurement counts with decimal=True."""
    counts = [{"00": 10, "01": 15}, {"10": 20, "11": 25}]
    expected = [{0: 10, 1: 15}, {2: 20, 3: 25}]
    result = normalize_counts(counts, decimal=True)
    assert result == expected


@pytest.mark.parametrize(
    "counts", [{0: 10, 1: 15, 3: 25}, {"0": 10, "1": 15, "3": 25}, {"00": 10, "01": 15, "11": 25}]
)
def test_format_counts_include_zero_values_decimal(counts):
    """Test format counts include_zero_values option in decimal form."""
    expected = {0: 10, 1: 15, 2: 0, 3: 25}
    result = format_counts(counts, include_zero_values=True, decimal=True)
    assert result == expected


def test_format_value_string(result_instance):
    """Test _format_value with a string input."""
    assert result_instance._format_value("hello") == "'hello'"


def test_format_value_enum(result_instance):
    """Test _format_value with an Enum input."""
    assert result_instance._format_value(ExperimentType.GATE_MODEL) == "GATE_MODEL"


def test_format_value_datetime(result_instance):
    """Test _format_value with a datetime input."""
    test_datetime = datetime.datetime(2023, 1, 1, 12, 0)
    assert result_instance._format_value(test_datetime) == "2023-01-01T12:00:00Z"


def test_format_value_dict(result_instance):
    """Test _format_value with a dict input."""
    test_dict = {"key1": "value1", "key2": "value2"}
    assert result_instance._format_value(test_dict) == "{key1: 'value1', key2: 'value2'}"


def test_format_value_dict_with_depth(result_instance):
    """Test _format_value with a nested dict input and depth limit."""
    test_dict = {"key1": {"nested_key": "nested_value"}}
    assert result_instance._format_value(test_dict, depth=2) == "{...}"


def test_format_value_list(result_instance):
    """Test _format_value with a list input."""
    test_list = ["item1", "item2", "item3"]
    assert result_instance._format_value(test_list) == "['item1', 'item2', 'item3']"


def test_format_value_list_with_depth(result_instance):
    """Test _format_value with a nested list and depth limit."""
    test_list = [["item1", "item2"], ["item3", "item4"]]
    assert result_instance._format_value(test_list, depth=2) == "[...]"


def test_format_value_dict_with_openqasm(result_instance):
    """Test _format_value with a dict with openQasm key."""
    test_dict = {"openQasm": "OPENQASM 2.0;"}
    assert result_instance._format_value(test_dict) == "{openQasm: '...'}"


def test_format_value_catch_all(result_instance):
    """Test _format_value with for catch-all repr."""
    assert result_instance._format_value(42) == "42"


def test_repr(result_instance):
    """Test __repr__ method of Result class."""
    expected_repr = (
        "Result(\n"
        "  device_id=test_device,\n"
        "  job_id=test_job,\n"
        "  success=True,\n"
        "  data=GateModelResultData(measurement_counts=None, measurements=None)"
    )
    assert repr(result_instance).startswith(expected_repr)
