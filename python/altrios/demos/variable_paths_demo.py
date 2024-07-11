"""
Script demonstrating how to use variable_path_list() and history_path_list()
demos to find the paths to variables within altrios classes.
"""

import altrios as alt

SAVE_INTERVAL = 1
# load hybrid consist
fc = alt.FuelConverter.default()

gen = alt.Generator.default()

edrv = alt.ElectricDrivetrain.default()

conv = alt.Locomotive.build_conventional_loco(
    fuel_converter=fc,
    generator=gen,
    drivetrain=edrv,
    loco_params=alt.LocoParams(
        pwr_aux_offset_watts=13e3,
        pwr_aux_traction_coeff_ratio=1.1e-3,
        force_max_newtons=667.2e3,
    ),
    save_interval=SAVE_INTERVAL,
)


# %%

pt = alt.PowerTrace.default()

sim = alt.LocomotiveSimulation(conv, pt, SAVE_INTERVAL)

# # print relative variable paths within locomotive simulation
# print("Locomotive simulation variable paths: ", sim.variable_path_list())
# # print relative history variable paths within locomotive simulation
# print("Locomotive simulation history variable paths: ", sim.history_path_list())

SHOW_PLOTS = False

SAVE_INTERVAL = 1

# https://docs.rs/altrios-core/latest/altrios_core/train/struct.TrainConfig.html
train_config = alt.TrainConfig(
    cars_empty=50,
    cars_loaded=50,
    rail_vehicle_type="Manifest",
    train_type=None,
    train_length_meters=None,
    train_mass_kilograms=None,
)

bel: alt.Locomotive = alt.Locomotive.default_battery_electric_loco()

# construct a vector of one BEL and several conventional locomotives
loco_vec = [bel] + [alt.Locomotive.default()] * 7
# instantiate consist
loco_con = alt.Consist(
    loco_vec,
    SAVE_INTERVAL,
)

tsb = alt.TrainSimBuilder(
    train_id="0",
    train_config=train_config,
    loco_con=loco_con,
)

rail_vehicle_file = "rolling_stock/rail_vehicles.csv"
rail_vehicle_map = alt.import_rail_vehicles(alt.resources_root() / rail_vehicle_file)
rail_vehicle = rail_vehicle_map[train_config.rail_vehicle_type]

network = alt.Network.from_file(
    alt.resources_root() / 'networks/simple_corridor_network.yaml')
# This data in this file were generated by running 
# ```python
# [lp.link_idx.idx for lp in sim0.path_tpc.link_points]
# ``` 
# in sim_manager_demo.py.
link_path = alt.LinkPath.from_csv_file(
    alt.resources_root() / "demo_data/link_points_idx_simple_corridor.csv")


speed_trace = alt.SpeedTrace.from_csv_file(
    alt.resources_root() / "demo_data/speed_trace_simple_corridor.csv"
)

train_sim: alt.SetSpeedTrainSim = tsb.make_set_speed_train_sim(
    rail_vehicle=rail_vehicle,
    network=network,
    link_path=link_path,
    speed_trace=speed_trace,
    save_interval=SAVE_INTERVAL,
)

# train_sim.variable_path_list()

# print relative variable paths within locomotive simulation
print("Locomotive simulation variable paths: ", train_sim.variable_path_list())
# print(type(train_sim.loco_con.loco_vec.tolist()[0].res))