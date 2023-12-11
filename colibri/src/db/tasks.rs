use std::fmt::{Display, LowerHex};

use serde::{Serialize, Deserialize, Serializer};
use serde_rusqlite::{columns_from_statement, from_row_with_columns};
use rusqlite::blob::Blob;

use crate::db::handler::Database;


#[derive(Serialize, Deserialize, Debug)]
struct AssetsAppearence{
    pub asset: String,
    pub location: String,

    #[serde(with = "serde_bytes")]
    pub tx_hash: Vec<u8>,
}


pub fn query_spam_transactions(db: &Database){
    let mut query = db.conn.prepare(
        "SELECT asset, location, tx_hash FROM history_events JOIN evm_events_info ON \
        history_events.identifier=evm_events_info.identifier
        "
    ).unwrap();
    let columns = columns_from_statement(&query);
    let assets_iter = query.query_map([], |row| Ok(from_row_with_columns::<AssetsAppearence>(row, &columns))).unwrap();
    for asset in assets_iter{
        println!("{:?}", asset.unwrap());
    }
}