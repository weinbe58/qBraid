# Copyright (C) 2024 qBraid
#
# This file is part of the qBraid-SDK
#
# The qBraid-SDK is free software released under the GNU General Public License v3
# or later. You can redistribute and/or modify it under the terms of the GPL v3.
# See the LICENSE file in the project root or <https://www.gnu.org/licenses/gpl-3.0.html>.
#
# THERE IS NO WARRANTY for the qBraid-SDK, as per Section 15 of the GPL v3.

"""
Unit tests for interfacing quantum programs

"""
import pytest

from qbraid._version import __version__
from qbraid.interface import circuits_allclose, random_circuit
from qbraid.interface.random.cirq_random import _cirq_random
from qbraid.interface.random.qasm3_random import _qasm3_random
from qbraid.interface.random.qiskit_random import _qiskit_random
from qbraid.programs.exceptions import QbraidError
from qbraid.transpiler import ConversionGraph, transpile


@pytest.mark.parametrize("num_qubits, depth, max_operands, seed", [(1, 1, 1, 42)])
def test_qasm3_random(num_qubits, depth, max_operands, seed):
    """Test that _qasm3_random generates the correct QASM code."""
    expected_output = f"""
// Generated by qBraid v{__version__}
OPENQASM 3.0;
include "stdgates.inc";
/*
    seed = {seed}
    num_qubits = {num_qubits}
    depth = {depth}
    max_operands = {max_operands}
*/
qubit[1] q;
bit[1] c;
x q[0];
c[0] = measure q[0];
"""
    output = random_circuit(
        "qasm3",
        num_qubits=num_qubits,
        depth=depth,
        max_operands=max_operands,
        seed=seed,
        measure=True,
    )
    assert output == expected_output


def test_bad_qasm3_random():
    """Test that _qasm3_random raises a QbraidError when it fails."""
    with pytest.raises(QbraidError):
        random_circuit("qasm3", seed="12")


@pytest.mark.parametrize("param", ["num_qubits", "depth"])
def test_qasm3_zero_value_raises(param):
    """Test that _qasm3_random raises a ValueError when a circuit parameter is <=0."""
    params = {param: 0}
    expected_err = f"Invalid random circuit option. '{param}' must be a positive integer."
    with pytest.raises(ValueError, match=expected_err):
        random_circuit("qasm3", **params)


@pytest.mark.parametrize("param", ["max_operands"])
def test_qasm3_zero_value_raises_for_max_operands(param):
    """Test that _qasm3_random raises a ValueError when a circuit parameter is <=0."""
    expected_err = f"Invalid random circuit option. '{param}' must be a positive integer."
    with pytest.raises(ValueError, match=expected_err):
        _qasm3_random(max_operands=0)


@pytest.mark.parametrize("package", ["qiskit", "cirq"])
def test_random_circuit_raises_for_bad_params(package: str, available_targets):
    """Test that _cirq_random raises a QbraidError for invalid parameters."""
    if package not in available_targets:
        pytest.skip(f"{package} not installed")

    err_msg = f"Failed to generate random circuit for program type '{package}'."
    with pytest.raises(QbraidError, match=err_msg):
        random_circuit(package, made_up_param=42)


def test_circuits_allclose(available_targets):
    """Test circuit allclose function."""
    pytket_available = "pytket" in available_targets
    braket_available = "braket" in available_targets
    qiskit_available = "qiskit" in available_targets

    if not (pytket_available and (braket_available or qiskit_available)):
        pytest.skip("Required quantum package(s) are not available")

    circuit0 = random_circuit("pytket", num_qubits=2, depth=2)

    if braket_available:
        circuit1 = transpile(circuit0, "braket")
        assert circuits_allclose(circuit1, circuit0, index_contig=True, allow_rev_qubits=True)

    if qiskit_available:
        circuit2 = random_circuit("qiskit", num_qubits=3, depth=2)
        assert not circuits_allclose(circuit2, circuit0, index_contig=True, allow_rev_qubits=True)


def test_bad_random_circuit():
    """Test that random_circuit raises a PackageValueError when given a bad package."""
    with pytest.raises(QbraidError):
        random_circuit("bad_package")


def test_raise_value_error_no_valid_generators():
    """Test raising ValueError when no valid generators are available"""
    with pytest.raises(
        ValueError, match="No registered generator that can create a random circuit for 'qasm2'"
    ):
        random_circuit("qasm2", graph=ConversionGraph(nodes=["qasm2", "qasm3"]))


def test_cirq_random_raises_for_bad_param():
    """Test that _cirq_random raises a ValueError when a circuit parameter is <=0."""
    with pytest.raises(QbraidError, match="Failed to create Cirq random circuit"):
        _cirq_random(1, 2, op_density=-1)


def test_qiskit_random_raises_for_bad_param():
    """Test that _qiskit_random raises a QbraidError when a circuit parameter is <=0."""
    with pytest.raises(QbraidError, match="Failed to create Qiskit random circuit"):
        _qiskit_random(1, 2, max_operands=-1)
