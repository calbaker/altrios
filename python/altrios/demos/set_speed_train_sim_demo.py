# %%
import time
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

import altrios as alt 
sns.set_theme()

SHOW_PLOTS = alt.utils.show_plots()

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

# instantiate battery model
# https://docs.rs/altrios-core/latest/altrios_core/consist/locomotive/powertrain/reversible_energy_storage/struct.ReversibleEnergyStorage.html#
res = alt.ReversibleEnergyStorage.from_file(
    alt.resources_root() / "powertrains/reversible_energy_storages/Kokam_NMC_75Ah_flx_drive.yaml"
)
# instantiate electric drivetrain (motors and any gearboxes)
# https://docs.rs/altrios-core/latest/altrios_core/consist/locomotive/powertrain/electric_drivetrain/struct.ElectricDrivetrain.html
edrv = alt.ElectricDrivetrain(
    pwr_out_frac_interp=[0., 1.],
    eta_interp=[0.98, 0.98],
    pwr_out_max_watts=5e9,
    save_interval=SAVE_INTERVAL,
)

loco_type = alt.BatteryElectricLoco(res, edrv)

bel: alt.Locomotive = alt.Locomotive(
    loco_type=loco_type,
    loco_params=alt.LocoParams.from_dict(dict(
        pwr_aux_offset_watts=8.55e3,
        pwr_aux_traction_coeff_ratio=540.e-6,
        force_max_newtons=667.2e3,
)))

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

rail_vehicle_file = "rolling_stock/" + train_config.rail_vehicle_type + ".yaml"
rail_vehicle = alt.RailVehicle.from_file(
    alt.resources_root() / rail_vehicle_file)

network = alt.Network.from_file(
    alt.resources_root() / "networks/Taconite-NoBalloon.yaml")
network.set_speed_set_for_train_type(alt.TrainType.Freight)
# file created from ./speed_limit_train_sim_demo.py:L92
link_path = alt.LinkPath.from_csv_file(
    alt.resources_root() / "demo_data/link_path.csv"
)

# file created from ./speed_limit_train_sim_demo.py:L105
speed_trace = alt.SpeedTrace.from_csv_file(
    alt.resources_root() / "demo_data/speed_trace.csv"
)

train_sim: alt.SetSpeedTrainSim = tsb.make_set_speed_train_sim(
    rail_vehicle=rail_vehicle,
    network=network,
    link_path=link_path,
    speed_trace=speed_trace,
    save_interval=SAVE_INTERVAL,
)

train_sim.set_save_interval(SAVE_INTERVAL)
t0 = time.perf_counter()
train_sim.walk()
t1 = time.perf_counter()
print(f'Time to simulate: {t1 - t0:.5g}')

fig, ax = plt.subplots(3, 1, sharex=True)
ax[0].plot(
    np.array(train_sim.history.time_seconds) / 3_600,
    np.array(train_sim.history.pwr_whl_out_watts) / 1e6,
    label="tract pwr",
)
ax[0].set_ylabel('Power [MW]')
ax[0].legend()

ax[1].plot(
    np.array(train_sim.history.time_seconds) / 3_600,
    np.array(train_sim.history.res_aero_newtons) / 1e3,
    label='aero',
)
ax[1].plot(
    np.array(train_sim.history.time_seconds) / 3_600,
    np.array(train_sim.history.res_rolling_newtons) / 1e3,
    label='rolling',
)
ax[1].plot(
    np.array(train_sim.history.time_seconds) / 3_600,
    np.array(train_sim.history.res_curve_newtons) / 1e3,
    label='curve',
)
ax[1].plot(
    np.array(train_sim.history.time_seconds) / 3_600,
    np.array(train_sim.history.res_bearing_newtons) / 1e3,
    label='bearing',
)
ax[1].plot(
    np.array(train_sim.history.time_seconds) / 3_600,
    np.array(train_sim.history.res_grade_newtons) / 1e3,
    label='grade',
)
ax[1].set_ylabel('Force [MN]')
ax[1].legend()

ax[-1].plot(
    np.array(train_sim.history.time_seconds) / 3_600,
    train_sim.speed_trace.speed_meters_per_second,
)
ax[-1].set_xlabel('Time [hr]')
ax[-1].set_ylabel('Speed [m/s]')

plt.suptitle("Set Speed Train Sim Demo")

if SHOW_PLOTS:
    plt.tight_layout()
    plt.show()

# %%

# DEBUGGING CELL
# TODO: delete this cell
# run `./speed_limit_train_sim_demo.py` interactively and then run this script, which will fail
# After it fails, you can still run this cell and generate plots 

fig, ax = plt.subplots(2, 1, sharex=True, figsize=(10, 8))

ax[0].plot(
    train_sim.history.time_hours,
    np.array(train_sim.history.pwr_res_watts) / 1e6,
    label='ssts',
)
ax[0].plot(
    train_sim_slts.history.time_hours,
    np.array(train_sim_slts.history.pwr_res_watts) / 1e6,
    label='slts',
    linestyle='--',
)
ax[0].set_ylim((
    0,
    np.array(train_sim.history.pwr_res_watts).max() / 1e6 * 1.05
))
ax[0].legend()
ax[0].set_ylabel("Power [MW]")

ax[1].plot(
    train_sim.history.time_hours,
    train_sim.history.speed_meters_per_second,
    label='ssts',
)
ax[1].plot(
    train_sim_slts.history.time_hours,
    train_sim_slts.history.speed_meters_per_second,
    label='slts',
    linestyle='--',
)
ax[1].legend()
ax[1].set_xlabel('Time [hr]')
ax[1].set_ylabel("Speed [m/s]")
ax[1].set_xlim((0, np.array(train_sim.history.time_hours)[-1] * 1.05))
ax[1].set_ylim((
    0,
    np.array(train_sim.history.speed_meters_per_second).max() * 1.05
))

# %%
