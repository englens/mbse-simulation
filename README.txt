Requirements:
    Python3 (Lastest version; deveopled on 3.7.0)
    simpy 4.0.1 (Lastest)
    pandas 1.1.5 (Lastest)
    Cameo Systems Modeler 19.0 SP3
    
Instructions for use:
    Import the Stereotype profile present in the example model. At minimum, your model must contain:
        1+ Actors (Blocks with the SimActor Stereotype)
        1 SimActivity, with a diagram defining a valid sequence
    All actions on the SimActivity must be SimActions. These may be customized for action-specfic properties
    All SimActions must be allocated to some actor. These may also be unallocated if the parent activity is itself allocated.
    Once the model is finished, save it as an .xml file.
    Open 'config.json', and configure the correct model file, main activity name, and run settings
    Run the Sim from terminal with "python cameo_sim.py"