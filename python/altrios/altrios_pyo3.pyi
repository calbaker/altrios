import altrios.altrios_pyo3 as altpy
from typing import Any, Dict, List, Optional
import polars as pl
from typing_extensions import Self
from typing import Union, Tuple
from dataclasses import dataclass

# TODO: udpate to include api for `force_max` and `mu`


class SerdeAPI(object):
    @classmethod
    def from_bincode(cls, bincode_str: str) -> Self: ...
    @classmethod
    def from_json(cls, json_str: str) -> Self: ...
    @classmethod
    def from_yaml(cls, yaml_str: str) -> Self: ...
    @classmethod
    def from_file(cls, filename: Path) -> Self: ...
    @classmethod
    def from_str(cls, contents: str, format: str) -> Self: ...
    def to_str(self, format:str) -> str: ...
    def to_file(self, filename: Path): ...
    def to_bincode(self) -> bytes: ...
    def to_json(self) -> str: ...
    def to_yaml(self) -> str: ...


class Consist(SerdeAPI):
    assert_limits: bool
    history: ConsistStateHistoryVec
    loco_vec: list[Locomotive]
    save_interval: int
    state: ConsistState
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def get_hct(self) -> Any: ...
    def get_save_interval(self) -> Any: ...
    def set_pdct_gss(self) -> Any: ...
    def set_pdct_prop(self) -> Any: ...
    def set_pdct_resgreedy(self) -> Any: ...
    def set_save_interval(self, save_interval: int): ...
    def __copy__(self) -> Any: ...


class ConsistSimulation(SerdeAPI):
    i: int
    loco_con: Consist
    power_trace: PowerTrace
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def get_save_interval(self) -> Any: ...
    def set_save_interval(self, save_interval: int): ...
    def walk(self) -> Any: ...
    def __copy__(self) -> Any: ...


class ConsistState(SerdeAPI):
    energy_fuel_joules: float
    energy_out_joules: float
    energy_res_joules: float
    i: int
    pwr_dyn_brake_max_watts: float
    pwr_fuel_watts: float
    pwr_out_max_non_reves_watts: float
    pwr_out_max_reves_watts: float
    pwr_out_max_watts: float
    pwr_out_req_watts: float
    pwr_out_unfulfilled_watts: float
    pwr_out_watts: float
    pwr_rate_out_max_watts_per_second: float
    pwr_regen_max_watts: float
    pwr_regen_unfulfilled_watts: float
    pwr_reves_watts: float
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...


class ConsistStateHistoryVec(SerdeAPI):
    energy_fuel_joules: list[float]
    energy_out_joules: list[float]
    energy_res_joules: list[float]
    i: list[int]
    pwr_dyn_brake_max_watts: list[float]
    pwr_fuel_watts: list[float]
    pwr_out_max_non_reves_watts: list[float]
    pwr_out_max_reves_watts: list[float]
    pwr_out_max_watts: list[float]
    pwr_out_req_watts: list[float]
    pwr_out_unfulfilled_watts: list[float]
    pwr_out_watts: list[float]
    pwr_rate_out_max_watts_per_second: list[float]
    pwr_regen_max_watts: list[float]
    pwr_regen_unfulfilled_watts: list[float]
    pwr_reves_watts: list[float]
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...
    def __len__(self) -> int: ...


class ElectricDrivetrain(SerdeAPI):
    eta_interp: list[float]
    history: ElectricDrivetrainStateHistoryVec
    pwr_in_frac_interp: list[float]
    pwr_out_frac_interp: list[float]
    pwr_out_max_watts: float
    save_interval: Optional[int]
    state: ElectricDrivetrainState
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...


class ElectricDrivetrainState(SerdeAPI):
    energy_elec_dyn_brake_joules: float
    energy_elec_prop_in_joules: float
    energy_loss_joules: float
    energy_mech_dyn_brake_joules: float
    energy_mech_prop_out_joules: float
    eta: float
    i: int
    pwr_elec_dyn_brake_watts: float
    pwr_elec_prop_in_watts: float
    pwr_loss_watts: float
    pwr_mech_dyn_brake_watts: float
    pwr_mech_out_max_watts: float
    pwr_mech_prop_out_watts: float
    pwr_mech_regen_max_watts: float
    pwr_rate_out_max_watts_per_second: float
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...


class ElectricDrivetrainStateHistoryVec(SerdeAPI):
    energy_elec_dyn_brake_joules: list[float]
    energy_elec_prop_in_joules: list[float]
    energy_loss_joules: list[float]
    energy_mech_dyn_brake_joules: list[float]
    energy_mech_prop_out_joules: list[float]
    eta: list[float]
    i: list[int]
    pwr_elec_dyn_brake_watts: list[float]
    pwr_elec_prop_in_watts: list[float]
    pwr_loss_watts: list[float]
    pwr_mech_dyn_brake_watts: list[float]
    pwr_mech_out_max_watts: list[float]
    pwr_mech_prop_out_watts: list[float]
    pwr_mech_regen_max_watts: list[float]
    pwr_rate_out_max_watts_per_second: list[float]
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...
    def __len__(self) -> int: ...


class FuelConverter(SerdeAPI):
    eta_interp: list[float]
    eta_max: float
    eta_range: float
    history: FuelConverterStateHistoryVec
    pwr_idle_fuel_watts: float
    pwr_out_frac_interp: list[float]
    pwr_out_max_watts: float
    pwr_ramp_lag_seconds: float
    save_interval: Optional[int]
    state: FuelConverterState
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...


class FuelConverterState(SerdeAPI):
    energy_brake_joules: float
    energy_fuel_joules: float
    energy_idle_fuel_joules: float
    energy_loss_joules: float
    engine_on: bool
    eta: float
    i: int
    pwr_fuel_watts: float
    pwr_brake_watts: float
    pwr_idle_fuel_watts: float
    pwr_loss_watts: float
    pwr_out_max_watts: float
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...


class FuelConverterStateHistoryVec(SerdeAPI):
    energy_brake_joules: list[float]
    energy_fuel_joules: list[float]
    energy_idle_fuel_joules: list[float]
    energy_loss_joules: list[float]
    engine_on: list[bool]
    eta: list[float]
    i: list[int]
    pwr_brake_watts: list[float]
    pwr_fuel_watts: list[float]
    pwr_idle_fuel_watts: list[float]
    pwr_loss_watts: list[float]
    pwr_out_max_watts: list[float]
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...
    def __len__(self) -> int: ...


class Generator(SerdeAPI):
    eta_interp: list[float]
    history: GeneratorStateHistoryVec
    pwr_in_frac_interp: list[float]
    pwr_out_frac_interp: list[float]
    pwr_out_max_watts: float
    save_interval: Optional[int]
    state: GeneratorState
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...


class GeneratorState(SerdeAPI):
    energy_elec_aux_joules: float
    energy_elec_prop_out_joules: float
    energy_loss_joules: float
    energy_mech_in_joules: float
    eta: float
    i: int
    pwr_elec_aux_watts: float
    pwr_elec_out_max_watts: float
    pwr_elec_prop_out_watts: float
    pwr_loss_watts: float
    pwr_mech_in_watts: float
    pwr_rate_out_max_watts_per_second: float
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...


class GeneratorStateHistoryVec(SerdeAPI):
    energy_elec_aux_joules: list[float]
    energy_elec_prop_out_joules: list[float]
    energy_loss_joules: list[float]
    energy_mech_in_joules: list[float]
    eta: list[float]
    i: list[int]
    pwr_elec_aux_watts: list[float]
    pwr_elec_out_max_watts: list[float]
    pwr_elec_prop_out_watts: list[float]
    pwr_loss_watts: list[float]
    pwr_mech_in_watts: list[float]
    pwr_rate_out_max_watts_per_second: list[float]
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...
    def __len__(self) -> int: ...


@dataclass
class LocoParams:
    pwr_aux_offset_watts: float
    pwr_aux_traction_coeff_ratio: float
    force_max_newtons: float
    mass_kilograms: Optional[float]

    @classmethod
    def from_dict(cls, param_dict: Dict[str, float]) -> Self:
        """
        Argument `param_dict` has keys matching attributes of class
        """
        ...


@dataclass
class ConventionalLoco(SerdeAPI):
    fc: FuelConverter
    gen: Generator
    edrv: ElectricDrivetrain


@dataclass
class HybridLoco(SerdeAPI):
    fuel_converter: FuelConverter
    generator: Generator
    reversible_energy_storage: ReversibleEnergyStorage
    electric_drivetrain: ElectricDrivetrain
    fuel_res_ratio: Optional[float]
    fuel_res_split: Optional[float]
    gss_interval: Optional[int]


@dataclass
class BatteryElectricLoco(SerdeAPI):
    res: ReversibleEnergyStorage
    edrv: ElectricDrivetrain


@dataclass
class DummyLoco(SerdeAPI): ...


class Locomotive(SerdeAPI):
    assert_limits: bool
    edrv: Any
    fc: FuelConverter
    fuel_res_ratio: float
    fuel_res_split: float
    gen: Generator
    history: LocomotiveStateHistoryVec
    pwr_aux_watts: float
    res: ReversibleEnergyStorage
    save_interval: int
    state: LocomotiveState

    @classmethod
    def __new__(
        cls,
        loco_type: Union[ConventionalLoco, HybridLoco, BatteryElectricLoco, DummyLoco],
        loco_params: LocoParams,
        ): ...
    @classmethod
    def build_battery_electric_loco(
        cls,
        reversible_energy_storage: ReversibleEnergyStorage,
        drivetrain: ElectricDrivetrain,
        loco_params: LocoParams,
        save_interval: Optional[int]
    ) -> Self: ...

    @classmethod
    def default_battery_electric_loco(cls) -> Locomotive: ...
    @classmethod
    def build_conventional_loco(
        cls,
        fuel_converter: FuelConverter,
        generator: Generator,
        drivetrain: ElectricDrivetrain,
        loco_params: LocoParams,
        save_interval: Optional[int],
    ) -> Self: ...
    @classmethod
    def build_dummy_loco(cls) -> Self: ...
    @classmethod
    def build_hybrid_loco(
        cls,
        fuel_converter: FuelConverter,
        generator: Generator,
        reversible_energy_storage: ReversibleEnergyStorage,
        drivetrain: ElectricDrivetrain,
        loco_params: LocoParams,
        fuel_res_split: Optional[float],
        fuel_res_ratio: Optional[float],
        gss_interval: Optional[int],
        save_interval: Optional[int],
    ) -> Self: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def get_save_interval(self) -> Any: ...
    def set_save_interval(self, save_interval: int): ...
    def __copy__(self) -> Any: ...


class LocomotiveSimulation(SerdeAPI):
    i: int
    loco_unit: Locomotive
    power_trace: PowerTrace
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    def get_save_interval(self) -> Any: ...
    def set_save_interval(self, save_interval: int): ...
    def walk(self) -> Any: ...
    def __copy__(self) -> Any: ...


class LocomotiveState(SerdeAPI):
    energy_aux_joules: float
    energy_out_joules: float
    i: int
    pwr_aux_watts: float
    pwr_out_max_watts: float
    pwr_out_watts: float
    pwr_rate_out_max_watts_per_second: float
    pwr_regen_max_watts: float
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...


class LocomotiveStateHistoryVec(SerdeAPI):
    energy_aux_joules: list[float]
    energy_out_joules: list[float]
    i: list[int]
    pwr_aux_watts: list[float]
    pwr_out_max_watts: list[float]
    pwr_out_watts: list[float]
    pwr_rate_out_max_watts_per_second: list[float]
    pwr_regen_max_watts: list[float]
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...
    def __len__(self) -> int: ...


@dataclass
class PowerTrace(SerdeAPI):
    time_seconds: list[float]
    pwr_watts: list[float]
    engine_on: Optional[list[bool]]
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...
    def __len__(self) -> int: ...
    def from_csv_file(pathstr: str) -> Self: ...


class Pyo3Vec2Wrapper(SerdeAPI):
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def is_empty(self) -> Any: ...
    def tolist(self) -> Any: ...
    def __copy__(self) -> Any: ...
    def __delitem__(self, other) -> Any: ...
    def __getitem__(self, index) -> Any: ...
    def __len__(self) -> Any: ...
    def __setitem__(self, index, object) -> Any: ...


class Pyo3Vec3Wrapper(SerdeAPI):
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def is_empty(self) -> Any: ...
    def tolist(self) -> Any: ...
    def __copy__(self) -> Any: ...
    def __delitem__(self, other) -> Any: ...
    def __getitem__(self, index) -> Any: ...
    def __len__(self) -> Any: ...
    def __setitem__(self, index, object) -> Any: ...


class Pyo3VecBoolWrapper(SerdeAPI):
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def from_yaml(cls) -> Self: ...
    def is_empty(self) -> Any: ...
    def tolist(self) -> Any: ...
    def __copy__(self) -> Any: ...
    def __delitem__(self, other) -> Any: ...
    def __getitem__(self, index) -> Any: ...
    def __len__(self) -> Any: ...
    def __setitem__(self, index, object) -> Any: ...


class Pyo3VecWrapper(SerdeAPI):
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def is_empty(self) -> Any: ...
    def tolist(self) -> Any: ...
    def __copy__(self) -> Any: ...
    def __delitem__(self, other) -> Any: ...
    def __getitem__(self, index) -> Any: ...
    def __len__(self) -> Any: ...
    def __setitem__(self, index, object) -> Any: ...


class ReversibleEnergyStorage(SerdeAPI):
    energy_capacity_joules: float
    eta_interp_values: list[list[list[float]]]
    history: ReversibleEnergyStorageStateHistoryVec
    max_soc: float
    min_soc: float
    pwr_out_max_watts: float
    save_interval: Optional[int]
    soc_hi_ramp_start: Optional[float]
    soc_lo_ramp_start: Optional[float]
    state: ReversibleEnergyStorageState
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...


class ReversibleEnergyStorageState(SerdeAPI):
    energy_aux_joules: float
    energy_loss_joules: float
    energy_out_chemical_joules: float
    energy_out_electrical_joules: float
    energy_out_propulsion_joules: float
    eta: float
    i: int
    max_soc: float
    min_soc: float
    pwr_aux_watts: float
    pwr_loss_watts: float
    pwr_out_chemical_watts: float
    pwr_out_electrical_watts: float
    pwr_out_max_watts: float
    pwr_out_propulsion_watts: float
    pwr_regen_max_watts: float
    soc: float
    soc_hi_ramp_start: float
    soc_lo_ramp_start: float
    soh: float
    temperature_celsius: float
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...


class ReversibleEnergyStorageStateHistoryVec(SerdeAPI):
    energy_aux_joules: list[float]
    energy_loss_joules: list[float]
    energy_out_chemical_joules: list[float]
    energy_out_electrical_joules: list[float]
    energy_out_propulsion_joules: list[float]
    eta: list[float]
    i: list[int]
    max_soc: list[float]
    min_soc: list[float]
    pwr_aux_watts: list[float]
    pwr_loss_watts: list[float]
    pwr_out_chemical_watts: list[float]
    pwr_out_electrical_watts: list[float]
    pwr_out_max_watts: list[float]
    pwr_out_propulsion_watts: list[float]
    pwr_regen_max_watts: list[float]
    soc: list[float]
    soc_hi_ramp_start: list[float]
    soc_lo_ramp_start: list[float]
    soh: list[float]
    temperature_celsius: list[float]
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...
    def __len__(self) -> int: ...


@dataclass
class SpeedTrace(SerdeAPI):
    time_seconds: list[float]
    speed_meters_per_second: list[float]
    engine_on: Optional[list[bool]]
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...
    def __len__(self) -> int: ...
    def from_csv_file(pathstr: str) -> Self: ...
    def to_csv_file(self, pathstr: str): ...


class TrainState:
    time_seconds: float
    i: int
    offset_meters: float
    offset_back_meters: float
    total_dist_meters: float
    link_idx_front: int
    offset_in_link_meters: float
    grade_front: float
    speed_meters_per_second: float
    speed_limit_meters_per_second: float
    speed_target_meters_per_second: float
    dt_seconds: float
    length_meters: float
    mass_static_kilograms: float
    mass_adj_kilograms: float
    mass_freight_kilograms: float
    weight_static_newtons: float
    res_rolling_newtons: float
    res_bearing_newtons: float
    res_davis_b_newtons: float
    res_aero_newtons: float
    res_grade_newtons: float
    res_curve_newtons: float
    grade_front: float
    elev_front_meters: float
    pwr_res_watts: float
    pwr_accel_watts: float
    pwr_whl_out_watts: float
    energy_whl_out_joules: float
    energy_whl_out_pos_joules: float
    energy_whl_out_neg_joules: float
    @classmethod
    def default(cls) -> TrainState: ...
    @classmethod
    def from_json(cls, json_str: str) -> TrainState: ...
    @classmethod
    def __new__(
        cls,
        length_meters: float,
        mass_static_kilograms: float,
        mass_adj_kilograms: float,
        mass_freight_kilograms: float,
        init_train_state: Optional[InitTrainState]
    ) -> Self: ...
    def to_json(self) -> str: ...
    @classmethod
    def from_yaml(cls, yaml_str: str) -> TrainState: ...
    def to_yaml(self) -> str: ...
    def clone(self) -> TrainState: ...
    def reset_orphaned(self) -> None: ...


class TrainStateHistoryVec(SerdeAPI):
    time_seconds: list[float]
    offset_meters: list[float]
    offset_back_meters: list[float]
    link_idx_front: list[int]
    offset_in_link_meters: list[float]
    grade_front: list[float]
    speed_meters_per_second: list[float]
    speed_limit_meters_per_second: list[float]
    speed_target_meters_per_second: list[float]
    dt_seconds: list[float]
    length_meters: list[float]
    mass_static_kilograms: list[float]
    mass_adj_kilograms: list[float]
    mass_freight_kilograms: list[float]
    max_fric_braking: list[float]
    weight_static_newtons: list[float]
    res_rolling_newtons: list[float]
    res_bearing_newtons: list[float]
    res_davis_b_newtons: list[float]
    res_aero_newtons: list[float]
    res_grade_newtons: list[float]
    res_curve_newtons: list[float]
    pwr_whl_out_watts: list[float]
    energy_whl_out_joules: list[float]
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...
    def __len__(self) -> int: ...


class SetSpeedTrainSim(SerdeAPI):
    loco_con: Consist
    state: TrainState
    speed_trace: SpeedTrace
    history: TrainStateHistoryVec
    i: int
    save_interval: Optional[int]

    @classmethod
    def __init__(
        cls,
        loco_con: Consist,
        state: TrainState,
        train_res_file: Optional[str],
        path_tpc_file: Optional[str],
        speed_trace: SpeedTrace,
        save_interval: Optional[int],
        simulation_days: Optional[int]
    ) -> None: ...

    def clone(self, *args, **kwargs) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...
    def set_save_interval(self, save_interval: int): ...


class LinkPoint(SerdeAPI):
    offset_meters: float
    grade_count: int
    curve_count: int
    cat_power_count: int
    link_idx: LinkIdx


class PathResCoeff(SerdeAPI):
    offset: float
    res_coeff: float
    res_net: float


class SpeedLimitPoint(SerdeAPI):
    offset: float
    speed_limit: float


class CatPowerLimit(SerdeAPI):
    offset_start: float
    offset_end: float
    power_limit: float
    district_id: Optional[str]


class TrainParams(SerdeAPI):
    length: float
    speed_max: float
    mass_total: float
    mass_per_brake: float
    axle_count: int
    train_type: TrainType
    curve_coeff_0: float
    curve_coeff_1: float
    curve_coeff_2: float


class PathTpc(SerdeAPI):
    link_points: List[LinkPoint]
    grades: List[PathResCoeff]
    curves: List[PathResCoeff]
    speed_points: List[SpeedLimitPoint]
    cat_power_limits: List[CatPowerLimit]
    train_params: TrainParams
    is_finished: bool


class BrakingPoint(SerdeAPI):
    offset_meters: float
    speed_limit_meters_per_second: float
    speed_target_meters_per_second: float



class BrakingPoints(SerdeAPI):
    points: List[BrakingPoint]
    idx_curr: int


class FricBrakeState(SerdeAPI):
    i: int
    force_newtons: float
    force_max_curr_newtons: float


class FricBrakeStateHistoryVec(SerdeAPI):
    i: List[int]
    force_newtons: List[float]
    force_max_curr_newtons: List[float]


class FricBrake(SerdeAPI):
    force_max_newtons: float
    ramp_up_time_seconds: float
    ramp_up_coeff_ratio: float
    state: FricBrakeState
    history: FricBrakeStateHistoryVec
    save_interval: Optional[int]



class SpeedLimitTrainSim(SerdeAPI):
    train_id: str
    origs: List[Location]
    dests: List[Location]
    loco_con: Consist
    state: TrainState
    # train_res: TrainRes # not accessible in Python
    path_tpc: PathTpc
    braking_points: BrakingPoints
    fric_brake: FricBrake
    history: TrainStateHistoryVec
    save_interval: Optional[int]
    simulation_days: Optional[int]
    scenario_year: Optional[int]

    @classmethod
    def __init__(
        cls,
        loco_con: Consist,
        state: TrainState,
        train_res_file: Optional[str],
        path_tpc_file: Optional[str],
        speed_trace: SpeedTrace,
        save_interval: Optional[int],
        simulation_days: Optional[int]
    ) -> None: ...

    def clone(self, *args, **kwargs) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def __copy__(self) -> Any: ...
    def set_save_interval(self, save_interval: int): ...
    def walk(self): ...
    def walk_timed_path(self, network: List[Link], timed_path: List[LinkIdxTime]): ...


class SpeedLimitTrainSimVec(SerdeAPI):
    @classmethod
    def default(cls) -> Self: ...
    def tolist(self) -> List[SpeedLimitTrainSim]: ...
    def set_save_interval(save_interal: int): ...


@dataclass
class LinkIdx(SerdeAPI):
    idx: int
    @classmethod
    def default(cls) -> Self: ...


class LinkIdxTime(SerdeAPI):
    link_idx: LinkIdx
    time_seconds: float
    @classmethod
    def default(cls) -> Self: ...


class TrainSimBuilder(SerdeAPI):
    train_id: str
    origin_id: str
    destination_id: str
    train_config: TrainConfig
    loco_con: Consist
    init_train_state: Optional[InitTrainState]
    drag_coeff_vec: Optional[List[float]]
    @classmethod
    def default(cls) -> Self: ...

    def __init__(
        self,
        train_id,
        origin_id,
        destination_id,
        train_config,
        loco_con,
        init_train_state
    ) -> None: ...

    def make_set_speed_train_sim(
        rail_vehicle: RailVehicle,
        network: List[Link],
        link_path: List[LinkIdx],
        speed_trace: SpeedTrace,
        save_interval: Optional[int],
    ) -> SetSpeedTrainSim:
        ...

    def make_speed_limit_train_sim(
        self,
        rail_vehicle: RailVehicle,
        location_map: Dict[str, List[Location]],
        save_interval: Optional[int],
        simulation_days: Optional[int],
        scenario_year: Optional[int],
    ) -> SpeedLimitTrainSim:
        ...


@dataclass
class TrainConfig(SerdeAPI):
    rail_vehicle_type: str
    cars_empty: int
    cars_loaded: int
    train_type: str
    train_length_meters: Optional[float]
    train_mass_kilograms: Optional[float]
    drag_coeff_vec: Optional[List[float]]
    @classmethod
    def default(cls) -> Self: ...


class RailVehicle(SerdeAPI):
    axle_count: int
    bearing_res_per_axle_newtons: float
    brake_count: int
    braking_ratio_empty: float
    braking_ratio_loaded: float
    car_type: str
    davis_b_seconds_per_meter: float
    drag_area_empty_square_meters: float
    drag_area_loaded_square_meters: float
    length_meters: float
    mass_extra_per_axle_kilograms: float
    mass_static_empty_kilograms: float
    mass_static_loaded_kilograms: float
    rolling_ratio: float
    speed_max_empty_meters_per_second: float
    speed_max_loaded_meters_per_second: float
    @classmethod
    def default(cls) -> Self: ...


class Location(SerdeAPI):
    location_id: str
    offset: float
    link_idx: LinkIdx
    is_front_end: bool
    grid_emissions_region: str
    electricity_price_region: str
    liquid_fuel_price_region: str
    @classmethod
    def default(cls) -> Self: ...


class EstTimeNet(SerdeAPI):
    @classmethod
    def default(cls) -> Self: ...
    def get_running_time_hours(self) -> float: ...


class Link(SerdeAPI):
    length_meters: float
    @classmethod
    def default(cls) -> Self: ...


class Elev(SerdeAPI):
    offset_meters: float
    elev_meters: float
    @classmethod
    def default(cls) -> Self: ...


class Heading(SerdeAPI):
    offset_meters: float
    heading: float
    lat: Optional[float]
    lon: Optional[float]
    @classmethod
    def default(cls) -> Self: ...

class SpeedSet(SerdeAPI): ...
    # TODO: finish fleshing this out

def import_locations(filename: str) -> Dict[str, List[Location]]: ...
def import_rail_vehicles(filename: str) -> Dict[str, RailVehicle]: ...


def build_speed_limit_train_sims(
    train_sim_builders: List[TrainSimBuilder],
    rail_veh_map: Dict[str, RailVehicle],
    location_map: Dict[str, List[Location]],
    save_interval: Optional[int],
    simulation_days: Optional[int],
    scenario_year: Optional[int]
) -> SpeedLimitTrainSimVec: ...


def run_speed_limit_train_sims(
    speed_limit_train_sim_vec: SpeedLimitTrainSimVec,
    network: List[Link],
    train_consist_plan: pl.DataFrame,
    loco_pool: pl.DataFrame,
    refuel_facilities: pl.DataFrame,
    timed_paths: List[List[LinkIdxTime]]
) -> List[SpeedLimitTrainSimVec, pl.DataFrame]: ...


def run_dispatch(
    network: List[Link],
    speed_limit_train_sims: SpeedLimitTrainSimVec,
    est_time_nets: List[EstTimeNet],
    print_train_move: bool,
    print_train_exit: bool,
) -> List[TimedLinkPath]: ...


def make_est_times(
    speed_limit_train_sim: SpeedLimitTrainSim,
    network: List[Link],
) -> Tuple[EstTimeNet, Consist]:
    ...


@dataclass
class TimedLinkPath(SerdeAPI):
    @classmethod
    def __new__(v: List[LinkIdxTime]) -> Self: ...
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def is_empty(self) -> Any: ...
    def tolist(self) -> Any: ...
    def __copy__(self) -> Any: ...
    def __delitem__(self, other) -> Any: ...
    def __getitem__(self, index) -> Any: ...
    def __len__(self) -> Any: ...
    def __setitem__(self, index, object) -> Any: ...


@dataclass
class Network(SerdeAPI):
    @classmethod
    def __new__(v: List[Link]) -> Self: ...
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def is_empty(self) -> Any: ...
    def tolist(self) -> Any: ...
    def __copy__(self) -> Any: ...
    def __delitem__(self, other) -> Any: ...
    def __getitem__(self, index) -> Any: ...
    def __len__(self) -> Any: ...
    def __setitem__(self, index, object) -> Any: ...
    def set_speed_set_for_train_type(self, train_type: TrainType): ...
    @classmethod
    def from_file_unchecked(cls, filename: Path) -> Self: ...

@dataclass
class LinkPath(SerdeAPI):
    @classmethod
    def __new__(v: List[LinkIdx]) -> Self: ...
    @classmethod
    def __init__(cls) -> None: ...
    def clone(self) -> Self: ...
    @classmethod
    def default(cls) -> Self: ...
    def is_empty(self) -> Any: ...
    def tolist(self) -> Any: ...
    def __copy__(self) -> Any: ...
    def __delitem__(self, other) -> Any: ...
    def __getitem__(self, index) -> Any: ...
    def __len__(self) -> Any: ...
    def __setitem__(self, index, object) -> Any: ...


@dataclass
class InitTrainState(SerdeAPI):
    time_seconds: float
    offset_meters: float
    speed_meters_per_second: float
    dt_seconds: float
    @classmethod
    def default(cls) -> Self: ...



@dataclass
class TrainType(SerdeAPI):
    Freight = altpy.TrainType.Freight,
    Passenger = altpy.TrainType.Passenger,
    Intermodal = altpy.TrainType.Intermodal,
    HighSpeedPassenger = altpy.TrainType.HighSpeedPassenger,
    TiltTrain = altpy.TrainType.TiltTrain,
    Commuter = altpy.TrainType.Commuter,
