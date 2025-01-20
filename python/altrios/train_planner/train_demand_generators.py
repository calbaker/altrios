from typing import Union, List, Dict, Callable
import polars as pl
import polars.selectors as cs
import pandas as pd
import numpy as np
import altrios as alt
from altrios.train_planner import planner_config, data_prep

def get_default_return_demand_generators() -> Dict[str, Callable]:
    return {
        'Unit': generate_return_demand_unit,
        'Manifest': generate_return_demand_manifest,
        'Intermodal': generate_return_demand_intermodal
    }

def initialize_reverse_empties(demand: Union[pl.LazyFrame, pl.DataFrame]) -> Union[pl.LazyFrame, pl.DataFrame]:
    """
    Swap `Origin` and `Destination` and append `_Empty` to `Train_Type`.
    Arguments:
    ----------
    demand: `DataFrame` or `LazyFrame` representing origin-destination demand.

    Outputs:
    ----------
    Updated demand `DataFrame` or `LazyFrame`.
    """
    return (demand
        .rename({"Origin": "Destination", "Destination": "Origin"})
        .with_columns((pl.concat_str(pl.col("Train_Type"),pl.lit("_Empty"))).alias("Train_Type"))
    )    

def generate_return_demand_unit(demand_subset: Union[pl.LazyFrame, pl.DataFrame], config: planner_config.TrainPlannerConfig) -> Union[pl.LazyFrame, pl.DataFrame]:
    """
    Given a set of Unit train demand for one or more origin-destination pairs, generate demand in the reverse direction(s).
    Arguments:
    ----------
    demand: `DataFrame` or `LazyFrame` representing origin-destination demand for Unit trains.

    Outputs:
    ----------
    Updated demand `DataFrame` or `LazyFrame` representing demand in the reverse direction(s) for each origin-destination pair.
    """
    return (demand_subset
        .pipe(initialize_reverse_empties)
    )

def generate_return_demand_manifest(demand_subset: Union[pl.LazyFrame, pl.DataFrame], config: planner_config.TrainPlannerConfig) -> Union[pl.LazyFrame, pl.DataFrame]:
    """
    Given a set of Manifest train demand for one or more origin-destination pairs, generate demand in the reverse direction(s).
    Arguments:
    ----------
    demand: `DataFrame` or `LazyFrame` representing origin-destination demand for Unit trains.

    Outputs:
    ----------
    Updated demand `DataFrame` or `LazyFrame` representing demand in the reverse direction(s) for each origin-destination pair.
    """
    return(demand_subset
        .pipe(initialize_reverse_empties)
        .with_columns((pl.col("Number_of_Cars") * config.manifest_empty_return_ratio).floor().cast(pl.UInt32))
    )

def generate_return_demand_intermodal(demand_subset: Union[pl.LazyFrame, pl.DataFrame], config: planner_config.TrainPlannerConfig) -> Union[pl.LazyFrame, pl.DataFrame]:
    """
    Given a set of Intermodal train demand for one or more origin-destination pairs, generate demand in the reverse direction(s).
    Arguments:
    ----------
    demand: `DataFrame` or `LazyFrame` representing origin-destination demand for Unit trains.

    Outputs:
    ----------
    Updated demand `DataFrame` or `LazyFrame` representing demand in the reverse direction(s) for each origin-destination pair.
    """
    return (demand_subset
        .pipe(initialize_reverse_empties)
        .with_columns(
            pl.concat_str(pl.min_horizontal("Origin", "Destination"), pl.lit("_"), pl.max_horizontal("Origin", "Destination")).alias("OD")
        )
        .with_columns(
            pl.col("Number_of_Cars", "Number_of_Containers").range().over("OD").name.suffix("_Return")
        )
        .filter(
            pl.col("Number_of_Cars") == pl.col("Number_of_Cars").max().over("OD"),
            pl.col("Number_of_Cars_Return") > 0
        )
        .drop("OD", "Number_of_Cars", "Number_of_Containers")
        .rename({"Number_of_Cars_Return": "Number_of_Cars",
                 "Number_of_Containers_Return": "Number_of_Containers"})
    )

def generate_return_demand(
    demand: pl.DataFrame,
    config: planner_config.TrainPlannerConfig
) -> pl.DataFrame:
    """
    Create a dataframe for additional demand needed for empty cars of the return trains
    Arguments:
    ----------
    df_annual_demand: The user_input file loaded by previous functions
    that contains loaded demand for each demand pair.
    config: Object storing train planner configuration paramaters
    Outputs:
    ----------
    df_return_demand: The demand generated by the need
    of returning the empty cars to their original nodes
    """
    demand_subsets = demand.partition_by("Train_Type", as_dict = True)
    return_demands = []
    for train_type, demand_subset in demand_subsets.items():
        train_type_label = train_type[0]
        if train_type_label in config.return_demand_generators:
            return_demand_generator = config.return_demand_generators[train_type_label]
            return_demand = return_demand_generator(demand_subset, config)
            return_demands.append(return_demand)
        else:
            print(f'Return demand generator not implemented for train type: {train_type_label}')

    demand_return = (pl.concat(return_demands, how="diagonal_relaxed")
        .filter(pl.col("Number_of_Cars") > 0)
    )
    return demand_return

def generate_manifest_rebalancing_demand(
    demand: pl.DataFrame,
    node_list: List[str],
    config: planner_config.TrainPlannerConfig
) -> pl.DataFrame:
    """
    Create a dataframe for summarized view of all origins' manifest demand
    in number of cars and received cars, both with loaded and empty counts
    Arguments:
    ----------
    demand: The user_input file loaded by previous functions
    that contains laoded demand for each demand pair.
    node_list: A list containing all the names of nodes in the system    
    config: Object storing train planner configuration paramaters

    Outputs:
    ----------
    origin_manifest_demand: The dataframe that summarized all the manifest demand
    originated from each node by number of loaded and empty cars
    with additional columns for checking the unbalance quantity and serve as check columns
    for the manifest empty car rebalancing function
    """
    def balance_trains(
    demand_origin_manifest: pl.DataFrame
    ) -> pl.DataFrame:
        """
        Update the manifest demand, especially the empty car demand to maintain equilibrium of number of
        cars dispatched and received at each node for manifest
        Arguments:
        ----------
        demand_origin_manifest: Dataframe that summarizes empty and loaded 
        manifest demand dispatched and received for each node by number cars
        Outputs:
        ----------
        demand_origin_manifest: Updated demand_origin_manifest with additional
        manifest empty car demand added to each node
        df_balance_storage: Documented additional manifest demand pairs and corresponding quantity for
        rebalancing process
        """
        df_balance_storage = pd.DataFrame(np.zeros(shape=(0, 4)))
        df_balance_storage = df_balance_storage.rename(
            columns={0: "Origin", 
                    1: "Destination", 
                    2: "Train_Type", 
                    3: "Number_of_Cars"})
        
        train_type = "Manifest_Empty"
        demand = demand_origin_manifest.to_pandas()[
            ["Origin","Manifest_Received","Manifest_Dispatched","Manifest_Empty"]]
        demand = demand.rename(columns={"Manifest_Received": "Received", 
                                "Manifest_Dispatched": "Dispatched",
                                "Manifest_Empty": "Empty"})

        step = 0
        # Calculate the number of iterations needed
        max_iter = len(demand) * (len(demand)-1) / 2
        while (~np.isclose(demand["Received"], demand["Dispatched"])).any() and (step <= max_iter):
            rows_def = demand[demand["Received"] < demand["Dispatched"]]
            rows_sur = demand[demand["Received"] > demand["Dispatched"]]
            if((len(rows_def) == 0) | (len(rows_sur) == 0)): 
                break
            # Find the first node that is in deficit of cars because of the empty return
            row_def = rows_def.index[0]
            # Find the first node that is in surplus of cars
            row_sur = rows_sur.index[0]
            surplus = demand.loc[row_sur, "Received"] - demand.loc[row_sur, "Dispatched"]
            df_balance_storage.loc[len(df_balance_storage.index)] = \
                [demand.loc[row_sur, "Origin"],
                demand.loc[row_def, "Origin"],
                train_type,
                surplus]
            demand.loc[row_def, "Received"] += surplus
            demand.loc[row_sur, "Dispatched"] = demand.loc[row_sur, "Received"]
            step += 1
            
        if (~np.isclose(demand["Received"], demand["Dispatched"])).any():
            raise Exception("While loop didn't converge")
        return pl.from_pandas(df_balance_storage)

    manifest_demand = (demand
        .filter(pl.col("Train_Type").str.strip_suffix("_Loaded") == "Manifest")
        .select(["Origin", "Destination","Number_of_Cars"])
        .rename({"Number_of_Cars": "Manifest"})
        .unique())
    
    origin_volume = manifest_demand.group_by("Origin").agg(pl.col("Manifest").sum())
    destination_volume = manifest_demand.group_by("Destination").agg(pl.col("Manifest").sum().alias("Manifest_Reverse"))
    origin_manifest_demand = (pl.DataFrame({"Origin": node_list})
        .join(origin_volume, left_on="Origin", right_on="Origin", how="left")
        .join(destination_volume, left_on="Origin", right_on="Destination", how="left")
        .with_columns(
            (pl.col("Manifest_Reverse") * config.manifest_empty_return_ratio).floor().cast(pl.UInt32).alias("Manifest_Empty"))
        .with_columns(
            (pl.col("Manifest") + pl.col("Manifest_Empty")).alias("Manifest_Dispatched"),
            (pl.col("Manifest_Reverse") + pl.col("Manifest") * config.manifest_empty_return_ratio).floor().cast(pl.UInt32).alias("Manifest_Received"))
        .drop("Manifest_Reverse")
        .filter((pl.col("Manifest").is_not_null()) | (pl.col("Manifest_Empty").is_not_null()))
    )

    return balance_trains(origin_manifest_demand)

def generate_demand_trains(
    demand: pl.DataFrame,
    demand_returns: pl.DataFrame,
    demand_rebalancing: pl.DataFrame,
    rail_vehicles: List[alt.RailVehicle],
    freight_type_to_car_type: Dict[str, str],
    config: planner_config.TrainPlannerConfig
) -> pl.DataFrame:
    """
    Generate a tabulated demand pair to indicate the final demand
    for each demand pair for each train type in number of trains
    Arguments:
    ----------
    demand: Tabulated demand for each demand pair for each train type in number of cars

    demand: The user_input file loaded and prepared by previous functions
    that contains loaded car demand for each demand pair.
    demand_returns: The demand generated by the need 
    of returning the empty cars to their original nodes
    demand_rebalancing: Documented additional manifest demand pairs and corresponding quantity for
    rebalancing process

    config: Object storing train planner configuration paramaters
    Outputs:
    ----------
    demand: Tabulated demand for each demand pair in terms of number of cars and number of trains
    """
    cars_per_train_min = (pl.from_dict(config.min_cars_per_train)
        .melt(variable_name="Train_Type", value_name="Cars_Per_Train_Min")
    )
    cars_per_train_min_default = (cars_per_train_min
        .filter(pl.col("Train_Type") == pl.lit("Default"))
        .select("Cars_Per_Train_Min").item()
    )
    cars_per_train_target = (pl.from_dict(config.target_cars_per_train)
        .melt(variable_name="Train_Type", value_name="Cars_Per_Train_Target")
    )
    cars_per_train_target_default = (cars_per_train_target
        .filter(pl.col("Train_Type") == pl.lit("Default"))
        .select("Cars_Per_Train_Target").item()
    )
             
    demand = (pl.concat([demand, demand_returns, demand_rebalancing], how="diagonal_relaxed")
        .group_by("Origin","Destination", "Train_Type")
            .agg(pl.col("Number_of_Cars").sum())
        .filter(pl.col("Number_of_Cars") > 0)
        .pipe(data_prep.appendTonsAndHP, rail_vehicles, freight_type_to_car_type, config)
        # Merge on cars_per_train_min if the user specified any
        .join(cars_per_train_min, on=["Train_Type"], how="left")
        # Merge on cars_per_train_target if the user specified any
        .join(cars_per_train_target, on=["Train_Type"], how="left")
        # Fill in defaults per train type wherever the user didn't specify OD-specific hp_per_ton
        .with_columns(
            pl.col("Cars_Per_Train_Min").fill_null(cars_per_train_min_default),
            pl.col("Cars_Per_Train_Target").fill_null(cars_per_train_target_default),
        )
    )
    loaded = (demand
        .filter(~pl.col("Train_Type").str.contains("_Empty"))
        .with_columns(
            pl.col("Number_of_Cars", "Tons_Per_Car", "HP_Required_Per_Ton", "Cars_Per_Train_Min", "Cars_Per_Train_Target").name.suffix("_Loaded")
        )
    )
    empty = (demand
        .filter(pl.col("Train_Type").str.contains("_Empty"))
        .with_columns(
            pl.col("Number_of_Cars", "Tons_Per_Car", "HP_Required_Per_Ton", "Cars_Per_Train_Min", "Cars_Per_Train_Target").name.suffix("_Empty"),
            pl.col("Train_Type").str.strip_suffix("_Empty")
        )
    )
    demand = (demand
        .select(pl.col("Origin", "Destination"), pl.col("Train_Type").str.strip_suffix("_Empty"))
        .unique()
        .join(loaded.select(cs.by_name("Origin", "Destination", "Train_Type") | cs.ends_with("_Loaded")), on=["Origin", "Destination", "Train_Type"], how="left")
        .join(empty.select(cs.by_name("Origin", "Destination", "Train_Type") | cs.ends_with("_Empty")), on=["Origin", "Destination", "Train_Type"], how="left")
        # Replace nulls with zero
        .with_columns(cs.float().fill_null(0.0), 
                      cs.by_dtype(pl.UInt32).fill_null(pl.lit(0).cast(pl.UInt32)),
                      cs.by_dtype(pl.Int64).fill_null(pl.lit(0).cast(pl.Int64)),
                      )
        .group_by("Origin", "Destination", "Train_Type")
            .agg(
                pl.col("Number_of_Cars_Loaded", "Number_of_Cars_Empty").sum(),
                pl.col("Tons_Per_Car_Loaded", "Tons_Per_Car_Empty", 
                       "HP_Required_Per_Ton_Loaded", "HP_Required_Per_Ton_Empty",
                       "Cars_Per_Train_Min_Loaded", "Cars_Per_Train_Min_Empty",
                       "Cars_Per_Train_Target_Loaded", "Cars_Per_Train_Target_Empty").mean(),
                pl.sum_horizontal("Number_of_Cars_Loaded", "Number_of_Cars_Empty").sum().alias("Number_of_Cars")
            )
        .with_columns(
            # If Cars_Per_Train_Min and Cars_Per_Train_Target "disagree" for empty vs. loaded, take the average weighted by number of cars
            ((pl.col("Cars_Per_Train_Min_Loaded").mul("Number_of_Cars_Loaded") + pl.col("Cars_Per_Train_Min_Empty").mul("Number_of_Cars_Empty")) / pl.col("Number_of_Cars")).alias("Cars_Per_Train_Min"),
            ((pl.col("Cars_Per_Train_Target_Loaded").mul("Number_of_Cars_Loaded") + pl.col("Cars_Per_Train_Target_Empty").mul("Number_of_Cars_Empty")) / pl.col("Number_of_Cars")).alias("Cars_Per_Train_Target")
        )
        .with_columns(
            pl.when(config.single_train_mode)
                .then(1)
                .when(pl.col("Number_of_Cars") == 0)
                .then(0)
                .when(pl.col("Cars_Per_Train_Target") == pl.col("Number_of_Cars"))
                .then(1)
                .when(pl.col("Cars_Per_Train_Target") <= 1.0)
                .then(pl.col("Number_of_Cars"))
                .otherwise(
                    pl.max_horizontal([
                        1,
                        pl.min_horizontal([
                            pl.col("Number_of_Cars").floordiv("Cars_Per_Train_Target") + 1,
                            pl.col("Number_of_Cars").floordiv("Cars_Per_Train_Min")
                        ])
                    ])
                ).cast(pl.UInt32).alias("Number_of_Trains"),
            pl.col("Number_of_Cars_Loaded").mul(config.containers_per_car).alias("Number_of_Containers_Loaded"),
            pl.col("Number_of_Cars_Empty").mul(config.containers_per_car).alias("Number_of_Containers_Empty"),
            pl.lit(config.simulation_days).alias("Number_of_Days")
        )
        .drop("Cars_Per_Train_Target_Loaded", "Cars_Per_Train_Target_Empty", "Cars_Per_Train_Min_Empty", "Cars_Per_Train_Min_Loaded")
    )
    return demand
