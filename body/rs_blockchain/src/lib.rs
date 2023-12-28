use std::ffi::{CString, CStr};
use std::os::raw::c_char;
use chrono::{Utc, DateTime};

struct Block {
    index: usize,
    timestamp: *const c_char,
    proof: *const c_char,
    previous_hash: *const c_char,
    encoded_model: *const c_char,
}

impl Default for Block {
    fn default() -> Block {
        let index = 0;
        let timestamp = CString::new(Utc::now().to_rfc3339()).unwrap().into_raw();
        let proof = CString::default().into_raw();
        let previous_hash = CString::default().into_raw();
        let encoded_model = CString::default().into_raw();

        Block {
            index,
            timestamp,
            proof,
            previous_hash,
            encoded_model
        }
    }
}

pub struct BlockChain {
    blocks: Vec<Block>,
}

impl BlockChain {
    pub fn new() -> Self {
        BlockChain { blocks: vec![Block::default()] }
    }

    pub fn add_block(&mut self, proof: String, encoded_model: String) {
        let index = self.blocks.len() + 1;
        let timestamp = CString::new(Utc::now().to_rfc3339()).unwrap().into_raw();
        let proof_cstring = CString::new(proof).unwrap().into_raw();
        let previous_proof = self.blocks.last().unwrap().proof;
        let encoded_model_cstring = CString::new(encoded_model).unwrap().into_raw();

        let block = Block {
            index,
            timestamp,
            proof: proof_cstring,
            previous_hash: previous_proof,
            encoded_model: encoded_model_cstring
        };

        self.blocks.push(block);
    }
}