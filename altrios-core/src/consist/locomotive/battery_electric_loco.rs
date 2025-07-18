use super::powertrain::electric_drivetrain::ElectricDrivetrain;
use super::powertrain::reversible_energy_storage::ReversibleEnergyStorage;
use super::powertrain::ElectricMachine;
use super::*;
use super::{LocoTrait, Mass, MassSideEffect};
use crate::imports::*;

#[serde_api]
#[derive(Default, Clone, Debug, PartialEq, Serialize, Deserialize, StateMethods, SetCumulative)]
#[cfg_attr(feature = "pyo3", pyclass(module = "altrios", subclass, eq))]
/// Battery electric locomotive
pub struct BatteryElectricLoco {
    #[has_state]
    pub res: ReversibleEnergyStorage,
    #[has_state]
    pub edrv: ElectricDrivetrain,
    /// control strategy for distributing power demand between `fc` and `res`
    #[has_state]
    #[serde(default)]
    pub pt_cntrl: BatteryPowertrainControls,
    // /// field for tracking current state
    // #[serde(default)]
    // pub state: BELState,
    // /// vector of [Self::state]
    // #[serde(default)]
    // pub history: BELStateHistoryVec,
}

#[pyo3_api]
impl BatteryElectricLoco {}

impl BatteryElectricLoco {
    /// Solve energy consumption for the current power output required
    /// Arguments:
    /// - pwr_out_req: tractive power required
    /// - dt: time step size
    pub fn solve_energy_consumption(
        &mut self,
        pwr_out_req: si::Power,
        dt: si::Time,
        pwr_aux: si::Power,
    ) -> anyhow::Result<()> {
        self.edrv.set_pwr_in_req(pwr_out_req, dt)?;
        if *self
            .edrv
            .state
            .pwr_elec_prop_in
            .get_fresh(|| format_dbg!())?
            > si::Power::ZERO
        {
            // positive traction
            self.res.solve_energy_consumption(
                *self
                    .edrv
                    .state
                    .pwr_elec_prop_in
                    .get_fresh(|| format_dbg!())?,
                pwr_aux,
                dt,
            )?;
        } else {
            // negative traction
            self.res.solve_energy_consumption(
                *self
                    .edrv
                    .state
                    .pwr_elec_prop_in
                    .get_fresh(|| format_dbg!())?,
                // limit aux power to whatever is actually available
                pwr_aux
                    // whatever power is available from regen plus normal
                    .min(
                        *self.res.state.pwr_prop_max.get_fresh(|| format_dbg!())?
                            - *self
                                .edrv
                                .state
                                .pwr_elec_prop_in
                                .get_fresh(|| format_dbg!())?,
                    )
                    .max(si::Power::ZERO),
                dt,
            )?;
        }
        Ok(())
    }
}

impl Mass for BatteryElectricLoco {
    fn mass(&self) -> anyhow::Result<Option<si::Mass>> {
        self.derived_mass().with_context(|| format_dbg!())
    }

    fn set_mass(
        &mut self,
        _new_mass: Option<si::Mass>,
        _side_effect: MassSideEffect,
    ) -> anyhow::Result<()> {
        Err(anyhow!(
            "`set_mass` not enabled for {}",
            stringify!(BatteryElectricLoco)
        ))
    }

    fn derived_mass(&self) -> anyhow::Result<Option<si::Mass>> {
        self.res.mass().with_context(|| format_dbg!())
    }

    fn expunge_mass_fields(&mut self) {
        self.res.expunge_mass_fields();
    }
}

impl Init for BatteryElectricLoco {
    fn init(&mut self) -> Result<(), Error> {
        self.res.init()?;
        self.edrv.init()?;
        self.pt_cntrl.init()?;
        Ok(())
    }
}
impl SerdeAPI for BatteryElectricLoco {}

impl LocoTrait for BatteryElectricLoco {
    fn set_curr_pwr_max_out(
        &mut self,
        pwr_aux: Option<si::Power>,
        _elev_and_temp: Option<(si::Length, si::ThermodynamicTemperature)>,
        train_mass: Option<si::Mass>,
        train_speed: Option<si::Velocity>,
        dt: si::Time,
    ) -> anyhow::Result<()> {
        let mass_for_loco: si::Mass = train_mass.with_context(|| {
            format!(
                "{}\n`train_mass_for_loco` must be provided for `BatteryElectricLoco` ",
                format_dbg!()
            )
        })?;
        let train_speed: si::Velocity = train_speed.with_context(|| {
            format!(
                "{}\n`train_speed` must be provided for `BatteryElectricLoco` ",
                format_dbg!()
            )
        })?;

        let disch_buffer: si::Energy = match &self.pt_cntrl {
            BatteryPowertrainControls::RGWDB(rgwb) => {
                (0.5 * mass_for_loco
                    * (rgwb
                        .speed_soc_disch_buffer
                        .with_context(|| format_dbg!())?
                        .powi(typenum::P2::new())
                        - train_speed.powi(typenum::P2::new())))
                .max(si::Energy::ZERO)
                    * rgwb
                        .speed_soc_disch_buffer_coeff
                        .with_context(|| format_dbg!())?
            }
        };
        let chrg_buffer: si::Energy = match &self.pt_cntrl {
            BatteryPowertrainControls::RGWDB(rgwb) => {
                (0.5 * mass_for_loco
                    * (train_speed.powi(typenum::P2::new())
                        - rgwb
                            .speed_soc_regen_buffer
                            .with_context(|| format_dbg!())?
                            .powi(typenum::P2::new())))
                .max(si::Energy::ZERO)
                    * rgwb
                        .speed_soc_regen_buffer_coeff
                        .with_context(|| format_dbg!())?
            }
        };

        self.res.set_curr_pwr_out_max(
            dt,
            pwr_aux.with_context(|| anyhow!(format_dbg!("`pwr_aux` not provided")))?,
            disch_buffer,
            chrg_buffer,
        )?;
        self.edrv.set_cur_pwr_max_out(
            *self.res.state.pwr_prop_max.get_fresh(|| format_dbg!())?,
            None,
        )?;
        self.edrv
            .set_cur_pwr_regen_max(*self.res.state.pwr_charge_max.get_fresh(|| format_dbg!())?)?;

        // power rate is never limiting in BEL, but assuming dt will be same
        // in next time step, we can synthesize a rate
        self.edrv.set_pwr_rate_out_max(
            (*self
                .edrv
                .state
                .pwr_mech_out_max
                .get_fresh(|| format_dbg!())?
                - *self
                    .edrv
                    .state
                    .pwr_mech_prop_out
                    .get_stale(|| format_dbg!())?)
                / dt,
        )?;
        Ok(())
    }

    fn get_energy_loss(&self) -> anyhow::Result<si::Energy> {
        Ok(*self.res.state.energy_loss.get_fresh(|| format_dbg!())?
            + *self.edrv.state.energy_loss.get_fresh(|| format_dbg!())?)
    }
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize, IsVariant, From, TryInto)]
pub enum BatteryPowertrainControls {
    /// Greedily uses [ReversibleEnergyStorage] with buffers that derate charge
    /// and discharge power inside of static min and max SOC range.  Also, includes
    /// buffer for forcing [FuelConverter] to be active/on.
    RGWDB(Box<RESGreedyWithDynamicBuffersBEL>),
}

impl Default for BatteryPowertrainControls {
    fn default() -> Self {
        Self::RGWDB(Default::default())
    }
}

impl Init for BatteryPowertrainControls {
    fn init(&mut self) -> Result<(), Error> {
        match self {
            Self::RGWDB(rgwb) => rgwb.init()?,
        }
        Ok(())
    }
}

impl SetCumulative for BatteryPowertrainControls {
    fn set_cumulative<F: Fn() -> String>(&mut self, dt: si::Time, loc: F) -> anyhow::Result<()> {
        match self {
            Self::RGWDB(rgwdb) => {
                rgwdb.set_cumulative(dt, || format!("{}\n{}", loc(), format_dbg!()))?
            }
        }
        Ok(())
    }
}

impl Step for BatteryPowertrainControls {
    fn step<F: Fn() -> String>(&mut self, loc: F) -> anyhow::Result<()> {
        match self {
            Self::RGWDB(rgwdb) => rgwdb.step(|| format!("{}\n{}", loc(), format_dbg!()))?,
        }
        Ok(())
    }
}

impl SaveState for BatteryPowertrainControls {
    fn save_state<F: Fn() -> String>(&mut self, loc: F) -> anyhow::Result<()> {
        match self {
            Self::RGWDB(rgwdb) => rgwdb.save_state(|| format!("{}\n{}", loc(), format_dbg!()))?,
        }
        Ok(())
    }
}

impl CheckAndResetState for BatteryPowertrainControls {
    fn check_and_reset<F: Fn() -> String>(&mut self, loc: F) -> anyhow::Result<()> {
        match self {
            Self::RGWDB(rgwdb) => {
                rgwdb.check_and_reset(|| format!("{}\n{}", loc(), format_dbg!()))?
            }
        }
        Ok(())
    }
}

impl StateMethods for BatteryPowertrainControls {}

/// Greedily uses [ReversibleEnergyStorage] with buffers that derate charge
/// and discharge power inside of static min and max SOC range.  Also, includes
/// buffer for forcing [FuelConverter] to be active/on. See [Self::init] for
/// default values.
#[serde_api]
#[derive(Clone, Debug, PartialEq, Deserialize, Serialize, Default, StateMethods, SetCumulative)]
#[cfg_attr(feature = "pyo3", pyclass(module = "altrios", subclass, eq))]
#[non_exhaustive]
pub struct RESGreedyWithDynamicBuffersBEL {
    /// RES energy delta from minimum SOC corresponding to kinetic energy of
    /// vehicle at this speed that triggers ramp down in RES discharge.
    pub speed_soc_disch_buffer: Option<si::Velocity>,
    /// Coefficient for modifying amount of accel buffer
    pub speed_soc_disch_buffer_coeff: Option<si::Ratio>,
    /// RES energy delta from maximum SOC corresponding to kinetic energy of
    /// vehicle at current speed minus kinetic energy of vehicle at this speed
    /// triggers ramp down in RES discharge
    pub speed_soc_regen_buffer: Option<si::Velocity>,
    /// Coefficient for modifying amount of regen buffer
    pub speed_soc_regen_buffer_coeff: Option<si::Ratio>,
    #[serde(default)]
    pub state: RGWDBStateBEL,
    #[serde(default)]
    /// history of current state
    pub history: RGWDBStateBELHistoryVec,
}

#[pyo3_api]
impl RESGreedyWithDynamicBuffersBEL {}

impl Init for RESGreedyWithDynamicBuffersBEL {
    fn init(&mut self) -> Result<(), Error> {
        init_opt_default!(self, speed_soc_disch_buffer, 40.0 * uc::MPH);
        init_opt_default!(self, speed_soc_disch_buffer_coeff, 1.0 * uc::R);
        init_opt_default!(self, speed_soc_regen_buffer, 10. * uc::MPH);
        init_opt_default!(self, speed_soc_regen_buffer_coeff, 1.0 * uc::R);
        Ok(())
    }
}
impl SerdeAPI for RESGreedyWithDynamicBuffersBEL {}

#[serde_api]
#[derive(
    Clone,
    Debug,
    Default,
    Deserialize,
    Serialize,
    PartialEq,
    HistoryVec,
    StateMethods,
    SetCumulative,
)]
#[serde(default)]
#[cfg_attr(feature = "pyo3", pyclass(module = "altrios", subclass, eq))]
/// State for [RESGreedyWithDynamicBuffers ]
pub struct RGWDBStateBEL {
    /// time step index
    pub i: TrackedState<usize>,
}

#[pyo3_api]
impl RGWDBStateBEL {}

impl Init for RGWDBStateBEL {}
impl SerdeAPI for RGWDBStateBEL {}
