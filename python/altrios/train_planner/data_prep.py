from typing import Union, List, Tuple
from pathlib import Path
import polars as pl
import polars.selectors as cs
import pandas as pd
import numpy as np
import altrios as alt
from altrios import defaults, utilities
from altrios.train_planner import planner_config

day_order_map = 

def load_freight_demand(
    demand_table: Union[pl.DataFrame, Path, str]
) -> Tuple[pl.DataFrame, pl.Series, int]:
    """
    Load the user input csv file into a dataframe for later processing
    Arguments:
    ----------
    user_input_file: path to the input csv file that user import to the module
    Example Input:
        Origin	Destination	Train_Type	Number_of_Cars	Number_of_Containers
        Barstow	Stockton	Unit	    2394	        0
        Barstow	Stockton	Manifest	2588	        0
        Barstow	Stockton	Intermodal	2221	        2221

    Outputs:
    ----------
    df_annual_demand: dataframe with all pair information including:
    origin, destination, train type, number of cars
    node_list: List of origin or destination demand nodes
    """
    if type(demand_table) is not pl.DataFrame:
        demand_table = pl.read_csv(demand_table, dtypes = {"Number_of_Cars": pl.UInt32, "Number_of_Containers": pl.UInt32})

    nodes = pl.concat(
        [demand_table.get_column("Origin"),
        demand_table.get_column("Destination")]).unique().sort()
    return demand_table, nodes

def prep_hourly_demand(
    total_demand: Union[pl.DataFrame, pl.LazyFrame],
    hourly_demand_density: Union[pl.DataFrame, pl.LazyFrame],
    daily_demand_density: Union[pl.DataFrame, pl.LazyFrame]
) -> Union[pl.DataFrame, pl.LazyFrame]:
    day_order_map = {
        "Mon": 1,
        "Tue": 2,
        "Wed": 3,
        "Thu": 4,
        "Fri": 5,
        "Sat": 6,
        "Sun": 7
    }
    return (total_demand
        .join(hourly_demand_density, how="inner", on=["Origin", "Destination"])
        .with_columns(
            (pl.col("Number_of_Containers") * pl.col("Percentage")).round(0).alias("Number_of_Containers_Daily"),
            pl.col("Day of Week").replace_strict(day_order_map).alias("Day_Order")
        )
        .join(hourly_demand_density, how="inner", on=["Origin", "Destination"])
        .sort("Origin", "Destination", "Day_Order", "Hour of Day")
        .with_columns(
            (pl.col("Number_of_Containers_Daily") * pl.col("Percentage_of_Hour")).round(0).alias("Number_of_Containers"),
            pl.concat_str(pl.col("Origin"), pl.lit("-"), pl.col("Destination")).alias("OD_Pair"),
            pl.int_range(0, pl.len()).over("Origin", "Destination").alias("Hour")
        )
        .with_columns(pl.col("Number_of_Containers").alias("Number_of_Cars"))
        .select("Origin", "Destination", "Train_Type", "Hour", "Number_of_Cars", "Number_of_Containers")
    )
    
def append_loco_info(loco_info: pd.DataFrame) -> pd.DataFrame:
    if all(item in loco_info.columns for item in [
        'HP','Loco_Mass_Tons','SOC_J','SOC_Min_J','SOC_Max_J','Capacity_J'
        ]
    ): return loco_info
    get_hp = lambda loco: loco.pwr_rated_kilowatts * 1e3 / alt.utils.W_PER_HP
    get_mass_ton = lambda loco: 0 if not loco.mass_kg else loco.mass_kg / alt.utils.KG_PER_TON
    get_starting_soc = lambda loco: defaults.DIESEL_TANK_CAPACITY_J if not loco.res else loco.res.state.soc * loco.res.energy_capacity_joules
    get_min_soc = lambda loco: 0 if not loco.res else loco.res.min_soc * loco.res.energy_capacity_joules
    get_max_soc = lambda loco: defaults.DIESEL_TANK_CAPACITY_J if not loco.res else loco.res.max_soc * loco.res.energy_capacity_joules
    get_capacity = lambda loco: defaults.DIESEL_TANK_CAPACITY_J if not loco.res else loco.res.energy_capacity_joules
    loco_info.loc[:,'HP'] = loco_info.loc[:,'Rust_Loco'].apply(get_hp) 
    loco_info.loc[:,'Loco_Mass_Tons'] = loco_info.loc[:,'Rust_Loco'].apply(get_mass_ton) 
    loco_info.loc[:,'SOC_J'] = loco_info.loc[:,'Rust_Loco'].apply(get_starting_soc) 
    loco_info.loc[:,'SOC_Min_J'] = loco_info.loc[:,'Rust_Loco'].apply(get_min_soc) 
    loco_info.loc[:,'SOC_Max_J'] = loco_info.loc[:,'Rust_Loco'].apply(get_max_soc) 
    loco_info.loc[:,'Capacity_J'] = loco_info.loc[:,'Rust_Loco'].apply(get_capacity) 
    return loco_info

def build_locopool(
    config: planner_config.TrainPlannerConfig,
    demand_file: Union[pl.DataFrame, Path, str],
    method: str = "tile",
    shares: List[float] = [],
    locomotives_per_node: int = None
) -> pl.DataFrame:
    """
    Generate default locomotive pool
    Arguments:
    ----------
    demand_file: Path to a file with origin-destination demand
    method: Method to determine each locomotive's type ("tile" or "shares_twoway" currently implemented)
    shares: List of shares for each locomotive type in loco_info (implemented for two-way shares only)
    Outputs:
    ----------
    loco_pool: Locomotive pool containing all locomotives' information that are within the system
    """
    config.loco_info = append_loco_info(config.loco_info)
    loco_types = list(config.loco_info.loc[:,'Locomotive_Type'])
    demand, node_list = demand_loader(demand_file)
    
    num_nodes = len(node_list)
    if locomotives_per_node is None:
        num_ods = demand.height
        cars_per_od = demand.get_column("Number_of_Cars").mean()
        if config.single_train_mode:
            initial_size = math.ceil(cars_per_od / config.cars_per_locomotive["Default"]) 
            rows = initial_size
        else:
            num_destinations_per_node = num_ods*1.0 / num_nodes*1.0
            initial_size = math.ceil((cars_per_od / config.cars_per_locomotive["Default"]) *
                                    num_destinations_per_node)  # number of locomotives per node
            rows = initial_size * num_nodes  # number of locomotives in total
    else:
        initial_size = locomotives_per_node
        rows = locomotives_per_node * num_nodes

    if config.single_train_mode:
        sorted_nodes = np.tile([demand.select(pl.col("Origin").first()).item()],rows).tolist()
        engine_numbers = range(0, rows)
    else:
        sorted_nodes = np.sort(np.tile(node_list, initial_size)).tolist()
        engine_numbers = rankdata(sorted_nodes, method="dense") * 1000 + \
            np.tile(range(0, initial_size), num_nodes)

    if method == "tile":
        repetitions = math.ceil(rows/len(loco_types))
        types = np.tile(loco_types, repetitions).tolist()[0:rows]
    elif method == "shares_twoway":
        # TODO: this logic can be replaced (and generalized to >2 types) using altrios.utilities.allocateItems
        if((len(loco_types) != 2) | (len(shares) != 2)):
            raise ValueError(
                f"""2-way prescribed locopool requested but number of locomotive types is not 2.""")

        idx_1 = np.argmin(shares)
        idx_2 = 1 - idx_1
        share_type_one = shares[idx_1]
        label_type_one = loco_types[idx_1]
        label_type_two = loco_types[idx_2]

        num_type_one = round(initial_size * share_type_one)
        if 0 == num_type_one:
            types = pd.Series([label_type_two] * initial_size)
        elif initial_size == num_type_one:
            types = pd.Series([label_type_one] * initial_size)
        else:
            # Arrange repeated sequences of type 1 + {type_two_per_type_one, type_two_per_type_one+1} type 2
            # so as to match the required total counts of each.
            type_two_per_type_one = (
                initial_size - num_type_one) / num_type_one
            # Number of type 1 + {type_two_per_bel+1} type 2 sequences needed
            num_extra_type_two = round(
                num_type_one * (type_two_per_type_one % 1.0))
            series_fewer_type_two = pd.Series(
                [label_type_one] + [label_type_two] * math.floor(type_two_per_type_one))
            series_more_type_two = pd.Series(
                [label_type_one] + [label_type_two] * math.ceil(type_two_per_type_one))
            types = np.concatenate((
                np.tile(series_more_type_two, num_extra_type_two),
                np.tile(series_fewer_type_two, num_type_one-num_extra_type_two)),
                axis=None)
        types = np.tile(types, num_nodes).tolist()
    else:
        raise ValueError(
            f"""Locopool build method '{method}' invalid or not implemented.""")

    loco_pool = pl.DataFrame(
        {'Locomotive_ID': pl.Series(engine_numbers, dtype=pl.UInt32),
         'Locomotive_Type': pl.Series(types, dtype=pl.Categorical),
         'Node': pl.Series(sorted_nodes, dtype=pl.Categorical),
         'Arrival_Time': pl.Series(np.zeros(rows), dtype=pl.Float64),
         'Servicing_Done_Time': pl.Series(np.zeros(rows), dtype=pl.Float64),
         'Refueling_Done_Time': pl.Series(np.tile(0, rows), dtype=pl.Float64),
         'Status': pl.Series(np.tile("Ready", rows), dtype=pl.Categorical),
         'SOC_Target_J': pl.Series(np.zeros(rows), dtype=pl.Float64),
         'Refuel_Duration': pl.Series(np.zeros(rows), dtype=pl.Float64),
         'Refueler_J_Per_Hr': pl.Series(np.zeros(rows), dtype=pl.Float64), 
         'Refueler_Efficiency': pl.Series(np.zeros(rows), dtype=pl.Float64), 
         'Port_Count': pl.Series(np.zeros(rows), dtype=pl.UInt32)}
    )

    loco_info_pl = pl.from_pandas(config.loco_info.drop(labels='Rust_Loco',axis=1),
        schema_overrides={'Locomotive_Type': pl.Categorical,
                          'Fuel_Type': pl.Categorical}
    )

    loco_pool = loco_pool.join(loco_info_pl, on="Locomotive_Type")
    return loco_pool

def build_refuelers(
    node_list: pd.Series,
    loco_pool: pl.DataFrame,
    refueler_info: pd.DataFrame,
    refuelers_per_incoming_corridor: int,
) -> pl.DataFrame:
    """
    Build the default set of refueling facilities.
    Arguments:
    ----------
    node_list: List of origin or destination demand nodes
    loco_pool: Locomotive pool
    refueler_info: DataFrame with information for each type of refueling infrastructure to use
    refuelers_per_incoming_corridor: Queue size per corridor arriving at each node.
    Outputs:
    ----------
    refuelers: Polars dataframe of facility county by node and type of fuel
    """
    ports_per_node = (loco_pool
        .group_by(pl.col("Locomotive_Type", "Fuel_Type").cast(pl.Utf8))
        .agg([(pl.lit(refuelers_per_incoming_corridor) * pl.len() / pl.lit(loco_pool.height))
              .ceil()
              .alias("Ports_Per_Node")])
        .join(pl.from_pandas(refueler_info),
              on=["Locomotive_Type", "Fuel_Type"], 
              how="left")
    )

    locations = pd.DataFrame(data={
        'Node': np.tile(node_list, ports_per_node.height)})
    locations = locations.sort_values(by=['Node']).reset_index(drop=True)

    refuelers = pl.DataFrame({
        'Node': pl.Series(locations['Node'], dtype=pl.Categorical).cast(pl.Categorical),
        'Refueler_Type': pl.Series(np.tile(
            ports_per_node.get_column("Refueler_Type").to_list(), len(node_list)), 
            dtype=pl.Categorical).cast(pl.Categorical),
        'Locomotive_Type': pl.Series(np.tile(
            ports_per_node.get_column("Locomotive_Type").to_list(), len(node_list)), 
            dtype=pl.Categorical).cast(pl.Categorical),
        'Fuel_Type': pl.Series(np.tile(
            ports_per_node.get_column("Fuel_Type").to_list(), len(node_list)), 
            dtype=pl.Categorical).cast(pl.Categorical),
        'Refueler_J_Per_Hr': pl.Series(np.tile(
            ports_per_node.get_column("Refueler_J_Per_Hr").to_list(), len(node_list)), 
            dtype=pl.Float64),
        'Refueler_Efficiency': pl.Series(np.tile(
            ports_per_node.get_column("Refueler_Efficiency").to_list(), len(node_list)), 
            dtype=pl.Float64),
        'Lifespan_Years': pl.Series(np.tile(
            ports_per_node.get_column("Lifespan_Years").to_list(), len(node_list)), 
            dtype=pl.Float64),
        'Cost_USD': pl.Series(np.tile(
            ports_per_node.get_column("Cost_USD").to_list(), len(node_list)), 
            dtype=pl.Float64),
        'Port_Count': pl.Series(np.tile(
            ports_per_node.get_column("Ports_Per_Node").to_list(), len(node_list)), 
            dtype=pl.UInt32)})
    return refuelers

def append_charging_guidelines(
    refuelers: pl.DataFrame,
    loco_pool: pl.DataFrame,
    demand: pl.DataFrame,
    network_charging_guidelines: pl.DataFrame
) -> pl.DataFrame:
    active_ods = demand.select(["Origin","Destination"]).unique()
    network_charging_guidelines = (network_charging_guidelines
        .join(active_ods, on=["Origin","Destination"], how="inner")
        .group_by(pl.col("Origin"))
        .agg(pl.col("Allowable_Battery_Headroom_MWh").min() * 1e6 / utilities.MWH_PER_MJ)
        .rename({"Allowable_Battery_Headroom_MWh": "Battery_Headroom_J"})
        .with_columns(pl.col("Origin").cast(pl.Categorical)))
    refuelers = (refuelers
        .join(network_charging_guidelines, left_on="Node", right_on="Origin", how="left")
        .with_columns(pl.when(pl.col("Fuel_Type")=="Electricity")
            .then(pl.col("Battery_Headroom_J"))
            .otherwise(0)
            .fill_null(0)
            .alias("Battery_Headroom_J")
            ))
    loco_pool = (loco_pool
        .join(network_charging_guidelines, left_on="Node", right_on="Origin", how="left")
        .with_columns(pl.when(pl.col("Fuel_Type")=="Electricity")
            .then(pl.col("Battery_Headroom_J"))
            .otherwise(0)
            .fill_null(0)
            .alias("Battery_Headroom_J"))
        .with_columns(pl.max_horizontal([pl.col('SOC_Max_J')-pl.col('Battery_Headroom_J'), pl.col('SOC_Min_J')]).alias("SOC_J")))
    return refuelers, loco_pool