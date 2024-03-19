pub mod kind;
pub mod method;

use crate::imports::*;
use crate::track::LinkPoint;
use crate::track::PathTpc;
use crate::train::TrainState;

#[enum_dispatch]
pub trait ResMethod {
    fn update_res(
        &mut self,
        state: &mut TrainState,
        path_tpc: &PathTpc,
        dir: &Dir,
    ) -> anyhow::Result<()>;
    fn fix_cache(&mut self, link_point_del: &LinkPoint);
}

/// Train resistance calculator that calculates resistive powers due to rolling, curvature, flange,
/// grade, and bearing resistances.  
// TODO: May also include inertial -- figure this out and modify doc string above
#[enum_dispatch(ResMethod)]
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, SerdeAPI)]
pub enum TrainRes {
    Point(method::Point),
    Strap(method::Strap),
}

impl Default for TrainRes {
    fn default() -> Self {
        Self::Strap(method::Strap::default())
    }
}

impl Valid for TrainRes {
    fn valid() -> Self {
        Self::Strap(method::Strap::valid())
    }
}

// #[cfg(test)]
// mod test_train_res {
//     use super::*;

//     #[test]
//     fn check_output() {
//         let file = File::create("train_res_test.yaml").unwrap();
//         serde_yaml::to_writer(file, &TrainRes::valid()).unwrap();
//     }
// }
