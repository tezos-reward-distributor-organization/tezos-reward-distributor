# TRD State Diagrams

## Launch life cycle:

<img src="launch_state_diagram.png" alt="drawing"/>

## Launch life cycle (with auto transitions):

<img src="launch_state_diagram_auto_transitions.png" alt="drawing"/>

## Configuration life cycle:

<img src="config_cycle_state_diagram.png" alt="drawing"/>

## Configuration life cycle (with auto transitions):

<img src="config_cycle_state_diagram_auto_transitions.png" alt="drawing"/>

## Diagram generation
To generate the state diagrams install graphviz:

```bash
sudo apt install graphviz
```

and import `GraphMachine` into TransitionsFsmBuilder.py and replace it with the actual machine instance and run trd normally.

```python
from transitions.extensions import GraphMachine as Machine
```

For more please check the [transitions diagram documentation](https://github.com/pytransitions/transitions#-diagrams).