use super::*;

#[altrios_api(
    #[new]
    #[pyo3(signature = (loco_vec, save_interval=None))]
    fn __new__(
        loco_vec: Vec<Locomotive>,
        save_interval: Option<usize>
    ) -> anyhow::Result<Self> {
        Ok(Self::new(loco_vec, save_interval, PowerDistributionControlType::default()))
    }

    #[getter("loco_vec")]
    fn get_loco_vec_py(&self) -> anyhow::Result<Pyo3VecLocoWrapper> {
        Ok(Pyo3VecLocoWrapper(self.loco_vec.clone()))
    }

    #[setter("loco_vec")]
    fn set_loco_vec_py(&mut self, loco_vec: Vec<Locomotive>) -> anyhow::Result<()> {
        self.set_loco_vec(loco_vec);
        Ok(())
    }

    #[pyo3(name="drain_loco_vec")]
    fn drain_loco_vec_py(&mut self, start: usize, end: usize) -> anyhow::Result<Pyo3VecLocoWrapper> {
        Ok(Pyo3VecLocoWrapper(self.drain_loco_vec(start, end)))
    }

    #[pyo3(name = "set_save_interval")]
    #[pyo3(signature = (save_interval=None))]
    /// Set save interval and cascade to nested components.
    fn set_save_interval_py(&mut self, save_interval: Option<usize>) -> anyhow::Result<()> {
        self.set_save_interval(save_interval);
        Ok(())
    }

    #[pyo3(name = "get_save_interval")]
    /// Set save interval and cascade to nested components.
    fn get_save_interval_py(&self) -> anyhow::Result<Option<usize>> {
        Ok(self.get_save_interval())
    }

    // methods setting values for hct, which is not directly exposed to python because enums
    // with fields are not supported by pyo3.

    /// Set hct to PowerDistributionControlType::Proportional
    fn set_pdct_prop(&mut self) {
        self.pdct = PowerDistributionControlType::Proportional(Proportional);
    }
    /// Set hct to PowerDistributionControlType::Greedy
    fn set_pdct_resgreedy(&mut self) {
        self.pdct = PowerDistributionControlType::RESGreedy(RESGreedy);
    }

    fn get_pdct(&self) -> String {
        // make a `describe` function
        match &self.pdct {
            PowerDistributionControlType::RESGreedy(val) => format!("{val:?}"),
            PowerDistributionControlType::Proportional(val) => format!("{val:?}"),
            PowerDistributionControlType::FrontAndBack(val) => format!("{val:?}"),
        }
    }

    #[setter("__assert_limits")]
    fn set_assert_limits_py(&mut self, val: bool) {
        self.set_assert_limits(val);
    }

    #[pyo3(name = "get_net_energy_res_joules")]
    fn get_net_energy_res_py(&self) -> f64 {
        self.get_net_energy_res().get::<si::joule>()
    }

    #[pyo3(name = "get_energy_fuel_joules")]
    fn get_energy_fuel_py(&self) -> f64 {
        self.get_energy_fuel().get::<si::joule>()
    }

    #[getter("force_max_lbs")]
    fn get_force_max_pounds_py(&self) -> anyhow::Result<f64> {
        Ok(self.force_max()?.get::<si::pound_force>())
    }

    #[getter("force_max_newtons")]
    fn get_force_max_newtons_py(&self) -> anyhow::Result<f64> {
        Ok(self.force_max()?.get::<si::newton>())
    }

    #[getter("mass_kg")]
    fn get_mass_kg_py(&self) -> anyhow::Result<Option<f64>> {
        Ok(self.mass()?.map(|m| m.get::<si::kilogram>()))
    }
)]
#[derive(Clone, Debug, PartialEq, Deserialize, Serialize)]
/// Struct for simulating power distribution controls and energy usage of locomotive consist.
pub struct Consist {
    // pretty sure these won't get automatically generated correctly
    #[api(skip_get, skip_set)]
    /// vector of locomotives, must be private to allow for side effects when setting
    pub loco_vec: Vec<Locomotive>,
    #[api(skip_set, skip_get)]
    /// power distribution control type
    pub pdct: PowerDistributionControlType,
    #[serde(default = "utils::return_true")]
    #[api(skip_set)] // setter needs to also apply to individual locomotives
    /// whether to panic if TPC requires more power than consist can deliver
    assert_limits: bool,
    #[serde(default)]
    #[serde(skip_serializing_if = "EqDefault::eq_default")]
    pub state: ConsistState,
    #[serde(default, skip_serializing_if = "ConsistStateHistoryVec::is_empty")]
    /// Custom vector of [Self::state]
    pub history: ConsistStateHistoryVec,
    #[api(skip_set, skip_get)] // custom needed for this
    save_interval: Option<usize>,
    #[serde(skip)]
    #[api(skip_get, skip_set)]
    n_res_equipped: Option<u8>,
}

impl Init for Consist {
    fn init(&mut self) -> Result<(), Error> {
        let _mass = self
            .mass()
            .map_err(|err| Error::InitError(format_dbg!(err)))?;
        self.set_pwr_dyn_brake_max();
        self.loco_vec.init()?;
        self.pdct.init()?;
        self.state.init()?;
        self.history.init()?;
        Ok(())
    }
}
impl SerdeAPI for Consist {}

impl Consist {
    pub fn new(
        loco_vec: Vec<Locomotive>,
        save_interval: Option<usize>,
        pdct: PowerDistributionControlType,
    ) -> Self {
        let mut consist = Self {
            state: Default::default(),
            loco_vec,
            history: Default::default(),
            save_interval,
            pdct,
            assert_limits: true,
            n_res_equipped: None,
        };
        let _ = consist.n_res_equipped();
        consist.set_save_interval(save_interval);
        consist
    }

    /// Returns number of RES-equipped locomotives
    pub fn n_res_equipped(&mut self) -> u8 {
        match self.n_res_equipped {
            Some(n_res_equipped) => n_res_equipped,
            None => {
                self.n_res_equipped = Some(self.loco_vec.iter().fold(0, |acc, loco| {
                    acc + if loco.reversible_energy_storage().is_some() {
                        1
                    } else {
                        0
                    }
                }));
                self.n_res_equipped.unwrap()
            }
        }
    }

    pub fn set_assert_limits(&mut self, val: bool) {
        self.assert_limits = val;
        for loco in self.loco_vec.iter_mut() {
            loco.assert_limits = val;
        }
    }

    pub fn force_max(&self) -> anyhow::Result<si::Force> {
        self.loco_vec.iter().enumerate().try_fold(
            0. * uc::N,
            |f_sum, (i, loco)| -> anyhow::Result<si::Force> {
                Ok(loco.force_max().with_context(|| {
                    format!(
                        "{}\nloco #: {}\nloco type: {}",
                        format_dbg!(),
                        i,
                        loco.loco_type.to_string()
                    )
                })? + f_sum)
            },
        )
    }

    pub fn get_loco_vec(&self) -> Vec<Locomotive> {
        self.loco_vec.clone()
    }

    pub fn set_loco_vec(&mut self, loco_vec: Vec<Locomotive>) {
        self.loco_vec = loco_vec;
    }

    pub fn drain_loco_vec(&mut self, start: usize, end: usize) -> Vec<Locomotive> {
        let loco_vec = self.loco_vec.drain(start..end).collect();
        loco_vec
    }

    pub fn get_save_interval(&self) -> Option<usize> {
        self.save_interval
    }

    pub fn set_save_interval(&mut self, save_interval: Option<usize>) {
        self.save_interval = save_interval;
        for loco in self.loco_vec.iter_mut() {
            loco.set_save_interval(save_interval);
        }
    }

    /// Set catenary charging/discharging power limit
    pub fn set_cat_power_limit(&mut self, path_tpc: &crate::track::PathTpc, offset: si::Length) {
        for cpl in path_tpc.cat_power_limits() {
            if offset < cpl.offset_start {
                break;
            } else if offset <= cpl.offset_end {
                self.state.pwr_cat_lim = cpl.power_limit;
                return;
            }
        }
        self.state.pwr_cat_lim = si::Power::ZERO;
    }

    pub fn get_energy_fuel(&self) -> si::Energy {
        self.loco_vec
            .iter()
            .map(|loco| match loco.loco_type {
                PowertrainType::BatteryElectricLoco(_) => si::Energy::ZERO,
                _ => loco.fuel_converter().unwrap().state.energy_fuel,
            })
            .sum::<si::Energy>()
    }

    pub fn get_net_energy_res(&self) -> si::Energy {
        self.loco_vec
            .iter()
            .map(|lt| match &lt.loco_type {
                PowertrainType::BatteryElectricLoco(loco) => loco.res.state.energy_out_chemical,
                PowertrainType::HybridLoco(loco) => loco.res.state.energy_out_chemical,
                _ => si::Energy::ZERO,
            })
            .sum::<si::Energy>()
    }

    pub fn set_pwr_aux(&mut self, engine_on: Option<bool>) -> anyhow::Result<()> {
        self.loco_vec
            .iter_mut()
            .for_each(|l| l.set_pwr_aux(engine_on));
        Ok(())
    }

    pub fn solve_energy_consumption(
        &mut self,
        pwr_out_req: si::Power,
        train_mass: Option<si::Mass>,
        train_speed: Option<si::Velocity>,
        dt: si::Time,
        engine_on: Option<bool>,
    ) -> anyhow::Result<()> {
        // TODO: account for catenary in here
        if self.assert_limits {
            ensure!(
                -pwr_out_req <= self.state.pwr_dyn_brake_max,
                "{}\nbraking power required ({} MW)\nexceeds max DB power ({} MW)",
                format_dbg!(),
                (-pwr_out_req.get::<si::megawatt>()).format_eng(Some(5)),
                self.state
                    .pwr_dyn_brake_max
                    .get::<si::megawatt>()
                    .format_eng(Some(5)),
            );
            ensure!(
                pwr_out_req <= self.state.pwr_out_max,
                "{}\npower required ({} MW)\nexceeds max power ({} MW)",
                format_dbg!(),
                pwr_out_req.get::<si::megawatt>().format_eng(Some(5)),
                self.state
                    .pwr_out_max
                    .get::<si::megawatt>()
                    .format_eng(Some(5))
            );
        }

        self.state.pwr_out_req = pwr_out_req;
        self.state.pwr_out_deficit =
            (pwr_out_req - self.state.pwr_out_max_reves).max(si::Power::ZERO);
        self.state.pwr_regen_deficit =
            (-pwr_out_req - self.state.pwr_regen_max).max(si::Power::ZERO);

        // Sum of dynamic braking capability, including regenerative capability
        self.set_pwr_dyn_brake_max();

        let pwr_out_vec: Vec<si::Power> = if pwr_out_req > si::Power::ZERO {
            // positive tractive power `pwr_out_vec`
            self.pdct.solve_positive_traction(
                &self.loco_vec,
                &self.state,
                train_mass,
                train_speed,
            )?
        } else if pwr_out_req < si::Power::ZERO {
            // negative tractive power `pwr_out_vec`
            self.pdct.solve_negative_traction(
                &self.loco_vec,
                &self.state,
                train_mass,
                train_speed,
            )?
        } else {
            // zero tractive power `pwr_out_vec`
            vec![si::Power::ZERO; self.loco_vec.len()]
        };

        self.state.pwr_out = pwr_out_vec
            .iter()
            .fold(si::Power::ZERO, |acc, &curr| acc + curr);

        if self.assert_limits {
            ensure!(
                utils::almost_eq_uom(&self.state.pwr_out_req, &self.state.pwr_out, None),
                format!(
                    "{}
                    self.state.pwr_out_req: {:.6} MW
                    self.state.pwr_out: {:.6} MW
                    self.state.pwr_out_deficit: {:.6} MW
                    pwr_out_vec: {:?}",
                    format_dbg!(),
                    &self.state.pwr_out_req.get::<si::megawatt>(),
                    &self.state.pwr_out.get::<si::megawatt>(),
                    &self.state.pwr_out_deficit.get::<si::megawatt>(),
                    &pwr_out_vec,
                )
            );
        }

        // maybe put logic for toggling `engine_on` here

        for (i, (loco, pwr_out)) in self.loco_vec.iter_mut().zip(pwr_out_vec.iter()).enumerate() {
            loco.solve_energy_consumption(*pwr_out, dt, engine_on, train_mass, train_speed)
                .with_context(|| {
                    format!(
                        "{}\nloco idx: {}, loco type: {}",
                        format_dbg!(),
                        i,
                        loco.loco_type.to_string()
                    )
                })?;
        }

        self.state.pwr_fuel = self
            .loco_vec
            .iter()
            .map(|loco| match &loco.loco_type {
                PowertrainType::ConventionalLoco(cl) => cl.fc.state.pwr_fuel,
                PowertrainType::HybridLoco(hel) => hel.fc.state.pwr_fuel,
                PowertrainType::BatteryElectricLoco(_) => si::Power::ZERO,
                PowertrainType::DummyLoco(_) => f64::NAN * uc::W,
            })
            .sum();

        self.state.pwr_reves = self
            .loco_vec
            .iter()
            .map(|loco| match &loco.loco_type {
                PowertrainType::ConventionalLoco(_cl) => si::Power::ZERO,
                PowertrainType::HybridLoco(hel) => hel.res.state.pwr_out_chemical,
                PowertrainType::BatteryElectricLoco(bel) => bel.res.state.pwr_out_chemical,
                PowertrainType::DummyLoco(_) => f64::NAN * uc::W,
            })
            .sum();

        self.state.energy_out += self.state.pwr_out * dt;
        if self.state.pwr_out >= 0. * uc::W {
            self.state.energy_out_pos += self.state.pwr_out * dt;
        } else {
            self.state.energy_out_neg -= self.state.pwr_out * dt;
        }
        self.state.energy_fuel += self.state.pwr_fuel * dt;
        self.state.energy_res += self.state.pwr_reves * dt;
        Ok(())
    }

    pub fn set_pwr_dyn_brake_max(&mut self) {
        self.state.pwr_dyn_brake_max = self
            .loco_vec
            .iter()
            .map(|loco| match &loco.loco_type {
                PowertrainType::ConventionalLoco(conv) => conv.edrv.pwr_out_max,
                PowertrainType::HybridLoco(hel) => hel.edrv.pwr_out_max,
                PowertrainType::BatteryElectricLoco(bel) => bel.edrv.pwr_out_max,
                // really big number that is not inf to avoid null in json
                PowertrainType::DummyLoco(_) => uc::W * 1e15,
            })
            .sum();
    }
}

impl Default for Consist {
    fn default() -> Self {
        let mut consist = Self {
            state: Default::default(),
            history: Default::default(),
            loco_vec: vec![
                Locomotive::default(),
                Locomotive::default_battery_electric_loco(),
                Locomotive::default_hybrid_electric_loco(),
                Locomotive::default(),
                Locomotive::default(),
                Locomotive::default(),
            ],
            assert_limits: true,
            save_interval: Some(1),
            n_res_equipped: Default::default(),
            pdct: Default::default(),
        };
        // ensure propagation to nested components
        consist.set_save_interval(Some(1));
        let _mass = consist.mass().unwrap();
        consist.init().unwrap();
        consist
    }
}

impl LocoTrait for Consist {
    fn set_curr_pwr_max_out(
        &mut self,
        pwr_aux: Option<si::Power>,
        elev_and_temp: Option<(si::Length, si::ThermodynamicTemperature)>,
        train_mass: Option<si::Mass>,
        train_speed: Option<si::Velocity>,
        dt: si::Time,
    ) -> anyhow::Result<()> {
        // TODO: this will need to account for catenary power
        // TODO: need to be able to configure regen to go to catenary or not
        // TODO: make sure that self.state includes catenary effects so that `solve_energy_consumption`
        // is operating with the same catenary power availability at the train position for which this
        // method is called
        ensure!(pwr_aux.is_none(), format_dbg!(pwr_aux.is_none()));

        // calculate mass assigned to each locomotive such that the buffer
        // calculations can be based on mass weighted proportionally to the
        // relative battery capacity
        let res_total_usable_energy = self.loco_vec.iter().fold(si::Energy::ZERO, |m_tot, l| {
            m_tot
                + l.reversible_energy_storage()
                    .map(|res| res.energy_capacity_usable())
                    .unwrap_or(si::Energy::ZERO)
        });
        for (i, loco) in self.loco_vec.iter_mut().enumerate() {
            // assign locomotive-specific mass for hybrid controls
            let mass: Option<si::Mass> = if res_total_usable_energy > si::Energy::ZERO {
                train_mass.map(|tm| {
                    loco.reversible_energy_storage()
                        .map(|res| res.energy_capacity_usable())
                        .unwrap_or(si::Energy::ZERO)
                        / res_total_usable_energy
                        * tm
                })
            } else {
                None
            };
            loco.set_curr_pwr_max_out(None, elev_and_temp, mass, train_speed, dt)
                .map_err(|err| {
                    err.context(format!(
                        "loco idx: {} loco type: {}",
                        i,
                        loco.loco_type.to_string()
                    ))
                })?;
        }
        self.state.pwr_out_max = self
            .loco_vec
            .iter()
            .fold(si::Power::ZERO, |acc, loco| acc + loco.state.pwr_out_max);
        self.state.pwr_rate_out_max =
            self.loco_vec.iter().fold(si::PowerRate::ZERO, |acc, loco| {
                acc + loco.state.pwr_rate_out_max
            });
        self.state.pwr_regen_max = self
            .loco_vec
            .iter()
            .fold(si::Power::ZERO, |acc, loco| acc + loco.state.pwr_regen_max);
        self.state.pwr_out_max_reves = self
            .loco_vec
            .iter()
            .map(|loco| match &loco.loco_type {
                PowertrainType::ConventionalLoco(_) => si::Power::ZERO,
                PowertrainType::HybridLoco(_) => loco.state.pwr_out_max,
                PowertrainType::BatteryElectricLoco(_) => loco.state.pwr_out_max,
                // really big number that is not inf to avoid null in json
                PowertrainType::DummyLoco(_) => 1e15 * uc::W,
            })
            .sum();
        self.state.pwr_out_max_non_reves = self.state.pwr_out_max - self.state.pwr_out_max_reves;

        Ok(())
    }

    fn step(&mut self) {
        for loco in self.loco_vec.iter_mut() {
            loco.step();
        }
        self.state.i += 1;
    }

    fn save_state(&mut self) {
        if let Some(interval) = self.save_interval {
            if self.state.i % interval == 0 {
                self.history.push(self.state);
                for loco in self.loco_vec.iter_mut() {
                    loco.save_state();
                }
            }
        }
    }

    fn get_energy_loss(&self) -> si::Energy {
        self.loco_vec
            .iter()
            .map(|loco| loco.get_energy_loss())
            .sum()
    }
}

impl Mass for Consist {
    fn mass(&self) -> anyhow::Result<Option<si::Mass>> {
        self.derived_mass()
    }

    fn derived_mass(&self) -> anyhow::Result<Option<si::Mass>> {
        ensure!(!self.loco_vec.is_empty());

        let init = self.loco_vec.first().unwrap().mass()?.is_none();
        if self
            .loco_vec
            .iter()
            .try_fold(init, |acc, l| -> anyhow::Result<bool> {
                if acc == l.mass()?.is_none() {
                    Ok(acc)
                } else {
                    Err(anyhow!(
                        "All elements in `loco_vec` must either be `None` or `Some`."
                    ))
                }
            })?
        {
            return Ok(None);
        }
        let mass = self.loco_vec.iter().enumerate().try_fold(
            0. * uc::KG,
            |m_acc, (i, loco)| -> anyhow::Result<si::Mass> {
                let loco_mass = loco
                    .mass()
                    .with_context(|| format_dbg!())?
                    .with_context(|| anyhow!("Locomotive {i} does not have `mass` set"))?;
                let new_mass: si::Mass = loco_mass + m_acc;
                Ok(new_mass)
            },
        )?;
        Ok(Some(mass))
    }

    fn expunge_mass_fields(&mut self) {
        self.loco_vec
            .iter_mut()
            .for_each(|l| l.expunge_mass_fields())
    }

    fn set_mass_specific_property(&mut self) -> anyhow::Result<()> {
        Err(anyhow!(
            "Setting mass specific properties not enabled at {} level",
            stringify!(Consist)
        ))
    }

    fn set_mass(
        &mut self,
        _mass: Option<si::Mass>,
        _side_effect: MassSideEffect,
    ) -> anyhow::Result<()> {
        Err(anyhow!(
            "Setting mass not enabled at {} level",
            stringify!(Consist)
        ))
    }
}
/// Locomotive State
/// probably reusable across all powertrain types
#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, HistoryVec)]
#[altrios_api]
pub struct ConsistState {
    /// current time index
    pub i: usize,

    /// maximum forward propulsive power consist can produce
    pub pwr_out_max: si::Power,
    /// maximum rate of increase of forward propulsive power consist can produce
    pub pwr_rate_out_max: si::PowerRate,
    /// maximum regen power consist can absorb at the wheel
    pub pwr_regen_max: si::Power,

    // limit variables
    /// maximum power that can be produced by
    /// [RES](locomotive::powertrain::reversible_energy_storage::ReversibleEnergyStorage)-equppped locomotives
    pub pwr_out_max_reves: si::Power,
    /// power demand not fulfilled by
    /// [RES](locomotive::powertrain::reversible_energy_storage::ReversibleEnergyStorage)-equipped locomotives
    pub pwr_out_deficit: si::Power,
    /// max power demand from
    /// non-[RES](locomotive::powertrain::reversible_energy_storage::ReversibleEnergyStorage)-equppped locomotives
    pub pwr_out_max_non_reves: si::Power,
    /// braking power demand not fulfilled as regen by [RES](locomotive::powertrain::reversible_energy_storage::ReversibleEnergyStorage)-equppped locomotives
    pub pwr_regen_deficit: si::Power,
    /// Total dynamic braking power of consist, based on sum of
    /// [electric-drivetrain](locomotive::powertrain::electric_drivetrain::ElectricDrivetrain)
    /// static limits across all locomotives (including regen).
    pub pwr_dyn_brake_max: si::Power,
    /// consist power output requested by [SpeedLimitTrainSim](crate::train::SpeedLimitTrainSim) or
    /// [SetSpeedTrainSim](crate::train::SetSpeedTrainSim)
    pub pwr_out_req: si::Power,
    /// Current consist/train-level catenary power limit
    pub pwr_cat_lim: si::Power,

    // achieved values
    /// Total tractive power of consist.
    /// Should always match [pwr_out_req](Self::pwr_out_req)] if `assert_limits == true`.
    pub pwr_out: si::Power,
    /// Total battery power of [RES](locomotive::powertrain::reversible_energy_storage::ReversibleEnergyStorage)-equppped locomotives
    pub pwr_reves: si::Power,
    /// Total fuel power of [FC](locomotive::powertrain::fuel_converter::FuelConverter)-equppped locomotives
    pub pwr_fuel: si::Power,

    /// Time-integrated energy form of [pwr_out](Self::pwr_out)
    pub energy_out: si::Energy,
    /// Energy out during positive or zero traction
    pub energy_out_pos: si::Energy,
    /// Energy out during negative traction (positive value means negative traction)
    pub energy_out_neg: si::Energy,
    /// Time-integrated energy form of [pwr_reves](Self::pwr_reves)
    pub energy_res: si::Energy,
    /// Time-integrated energy form of [pwr_fuel](Self::pwr_fuel)
    pub energy_fuel: si::Energy,
}

impl Init for ConsistState {}
impl SerdeAPI for ConsistState {}

impl Default for ConsistState {
    fn default() -> Self {
        Self {
            i: 1,
            pwr_out_max: Default::default(),
            pwr_rate_out_max: Default::default(),
            pwr_regen_max: Default::default(),

            // limit variables
            pwr_out_max_reves: Default::default(),
            pwr_out_deficit: Default::default(),
            pwr_out_max_non_reves: Default::default(),
            pwr_regen_deficit: Default::default(),
            pwr_dyn_brake_max: Default::default(),
            pwr_out_req: Default::default(),
            pwr_cat_lim: Default::default(),

            // achieved values
            pwr_out: Default::default(),
            pwr_reves: Default::default(),
            pwr_fuel: Default::default(),

            energy_out: Default::default(),
            energy_out_pos: Default::default(),
            energy_out_neg: Default::default(),

            energy_res: Default::default(),
            energy_fuel: Default::default(),
        }
    }
}
