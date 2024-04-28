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
Module containing function to convert from Amazon Braket to PyTKET.

"""

from typing import TYPE_CHECKING

from qbraid.transpiler.annotations import requires_extras

if TYPE_CHECKING:
    import braket.circuits
    import pytket.circuit


@requires_extras("pytket.extensions.braket")
def braket_to_pytket(circuit: "braket.circuits.Circuit") -> "pytket.circuit.Circuit":
    """Returns a pytket circuit equivalent to the input Amazon Braket circuit.

    Args:
        circuit (braket.circuits.Circuit): Braket circuit to convert to a pytket circuit.

    Returns:
        pytket.circuit.Circuit: PyTKET circuit object equivalent to input Braket circuit.
    """
    # pylint: disable-next=import-outside-toplevel
    from pytket.extensions.braket import braket_convert  # type: ignore

    return braket_convert.braket_to_tk(circuit)
