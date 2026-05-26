from sim_plane.backends.demo import DemoBackend
from sim_plane.backends.ego_planner import EgoPlannerBackend
from sim_plane.backends.ego_planner_fast_lio_marsim import EgoPlannerFastLIOMARSIMBackend
from sim_plane.backends.ego_planner_marsim import EgoPlannerMARSIMBackend
from sim_plane.backends.ego_planner_swarm import EgoPlannerSwarmBackend
from sim_plane.backends.ego_planner_swarm_fast_lio_marsim import EgoPlannerSwarmFastLIOMARSIMBackend
from sim_plane.backends.ego_planner_swarm_marsim import EgoPlannerSwarmMARSIMBackend
from sim_plane.backends.fast_lio_marsim import FastLIOMARSIMBackend
from sim_plane.backends.marsim import MARSIMBackend
from sim_plane.backends.px4_gazebo_classic import PX4GazeboClassicBackend
from sim_plane.backends.px4_jsbsim import PX4JSBSimBackend
from sim_plane.backends.px4_sih import PX4SIHBackend


def available_backends():
    return {
        DemoBackend.name: DemoBackend,
        EgoPlannerBackend.name: EgoPlannerBackend,
        EgoPlannerFastLIOMARSIMBackend.name: EgoPlannerFastLIOMARSIMBackend,
        EgoPlannerMARSIMBackend.name: EgoPlannerMARSIMBackend,
        EgoPlannerSwarmBackend.name: EgoPlannerSwarmBackend,
        EgoPlannerSwarmFastLIOMARSIMBackend.name: EgoPlannerSwarmFastLIOMARSIMBackend,
        EgoPlannerSwarmMARSIMBackend.name: EgoPlannerSwarmMARSIMBackend,
        FastLIOMARSIMBackend.name: FastLIOMARSIMBackend,
        MARSIMBackend.name: MARSIMBackend,
        PX4GazeboClassicBackend.name: PX4GazeboClassicBackend,
        PX4JSBSimBackend.name: PX4JSBSimBackend,
        PX4SIHBackend.name: PX4SIHBackend,
    }
