use alloy::providers::Provider;

pub struct NodeInquirer {
    pub chain_id: usize,
    pub nodes: Vec<Box<dyn Provider>>  // Using Box to make it sized
}