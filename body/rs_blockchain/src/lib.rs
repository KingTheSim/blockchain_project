use core::time;
use std::ffi::{CString, CStr};
use std::os::raw::c_char;
use chrono::{Utc, DateTime};
use blake3::Hasher;

struct Block {
    index: usize,
    timestamp: *const c_char,
    proof: *const c_char,
    hash: *const c_char,
    previous_hash: *const c_char,
    encoded_model: *const c_char,
}

impl Block {
    fn new(index: usize, timestamp: *mut i8, proof: *mut i8, hash: *mut i8, previous_hash: *const i8, encoded_model: *mut i8) -> Self {
        Block {
            index,
            timestamp,
            proof,
            hash,
            previous_hash,
            encoded_model
        }
    }

    fn calculate_hash(index: usize, timestamp: *const c_char, proof: *const c_char, previous_hash: *const c_char, encoded_model: *const c_char) -> String {
        let content = format!(
            "{}{}{}{}{}",
            index,
            unsafe { CStr::from_ptr(timestamp).to_string_lossy() },
            unsafe { CStr::from_ptr(proof).to_string_lossy() },
            unsafe { CStr::from_ptr(previous_hash).to_string_lossy() },
            unsafe { CStr::from_ptr(encoded_model).to_string_lossy() }
        );

        let mut hasher = Hasher::new();
        hasher.update(content.as_bytes());
        let hash = hasher.finalize();
        hash.to_hex().to_string()
    }
}

impl Default for Block {
    fn default() -> Block {
        let index = 0;
        let timestamp = CString::new(Utc::now().to_rfc3339()).unwrap().into_raw();
        let proof = CString::default().into_raw();
        let hash = CString::default().into_raw();
        let previous_hash = CString::default().into_raw();
        let encoded_model = CString::default().into_raw();

        Block {
            index,
            timestamp,
            proof,
            hash,
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
        let index = self.blocks.len();
        let timestamp = CString::new(Utc::now().to_rfc3339()).unwrap().into_raw();
        let proof_cstring = CString::new(proof).unwrap().into_raw();
        let previous_hash = self.blocks.last().unwrap().proof;
        let encoded_model_cstring = CString::new(encoded_model).unwrap().into_raw();

        let hash = CString::new(Block::calculate_hash(index, timestamp, proof_cstring, previous_hash, encoded_model_cstring)).unwrap().into_raw();

        let block = Block::new(index, timestamp, proof_cstring, hash, previous_hash, encoded_model_cstring);

        self.blocks.push(block);
    }
}