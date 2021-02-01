from typing import Any, Sequence, Dict, Iterable, Union

######################

from circuits.qubit import qB_Qubit

from braket.circuits.qubit_set import QubitSet as aws_QubitSet

from cirq.ops.qubit_order import QubitOrder as cirq_QubitOrder

#######################

qB_QubitSetInput = Union["aws_QubitSet", "cirq_QubitOrder", Iterable[qB_Qubit], Iterable[str], Iterable[int]]  

class qB_QubitSet():
    
    """
    A holder instance of qB_QubitSet has one property: self._qubitset, which returns the original aws_QubitSet, etc. object passed for it to hold.
    
    A definitive instance of qB_QubitSet is made from passing an iterable of the int or str names to define the qubits. In this case self._qubitset is the identity.
    
    To get from a holder instance to definitive instance, the to_qB() method grabs the necessary data that defines the definitive instance
        from the held aws_QubitSet, etc. object and modifies the instance in place by redefinition.
    """
    
    def __init__(self, qubitset: qB_QubitSetInput = None):
        
        self._holding = True
            
        if type(qubitset) == Iterable[str] or type(qubitset) == Iterable[int]:
            self._holding = False
            qubitset = [qB_Qubit(qubit) for qubit in qubitset]
            
        if type(qubitset) == Iterable[qB_Qubit]:
            self._holding = False
            self.qubits = qubitset
            
            self._qubitset = self
            
        if self._holding:
            self._qubitset = qubitset
        
    def __str__(self):
        if self._holding:
            return str(self._qubitset)
        return 'qB_QubitSet('+str([str(qubit) for qubit in self._qubitset])+')'
    
    #####################################
    
    def to_qB(self):
        if type(self._qubitset) != qB_QubitSet:
            try:
                qubitset = [int(qubit) for qubit in self._qubitset]
            except:
                qubitset = [str(qubit) for qubit in self._qubitset]
                
            return qB_QubitSet(qubitset)
            
    #######################################