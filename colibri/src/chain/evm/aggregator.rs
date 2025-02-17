use async_sqlite::Client;
use fallible_iterator::FallibleIterator;
use alloy::providers::ProviderBuilder;
use reqwest::Url;
use eyre::Result;

use crate::chain::evm::node::NodeInquirer;

pub struct EvmChainAggregator {
    pub ethereum_aggregator: NodeInquirer
}

impl EvmChainAggregator {
    pub fn new() -> Self {
        Self {
            ethereum_aggregator: NodeInquirer {chain_id: 1, nodes: Vec::new()}
        }
    }

    pub async fn init_nodes(&mut self, db_client: &Client) -> Result<()> {
        for blockchain in [&mut self.ethereum_aggregator] {
            let results = db_client.conn(|conn| {
                Ok(conn.prepare("SELECT endpoint FROM rpc_nodes WHERE blockchain=? and active=1")
                    .unwrap()
                    .query(["ETH"])
                    .unwrap()
                    .map(|row| Ok(row.get::<_, String>(0).unwrap()))
                    .collect::<Vec<String>>()
                    .unwrap())
            }).await?;

            for rpc_uri in results.iter() {
                if rpc_uri.len() == 0 { continue; }
                println!("===> {}", rpc_uri);
                blockchain.nodes.push(Box::new(ProviderBuilder::new().on_http(Url::parse(rpc_uri)?)));
            }
            println!("{:?}", results);
        }

        Ok(())

    }
}