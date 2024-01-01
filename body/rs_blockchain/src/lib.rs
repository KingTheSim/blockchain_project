use core::time;
use std::ffi::CStr;
use std::time::Instant;
use chrono::{Utc, DateTime};
use blake3::Hasher;
use rusqlite::{params, Connection, ffi::Error};
use serde::{Serialize, Deserialize};
use serde_json::json;

const DIFFICULTY: usize = 4;

#[derive(Serialize, Deserialize, Debug)]
pub struct Block {
    index: usize,
    timestamp: String,
    proof: usize,
    hash: String,
    previous_hash: String,
    encoded_model: String,
}

impl Block {
    pub fn new(index: usize, timestamp: String, previous_hash: String, encoded_model: String) -> Self {
        let proof = Block::proof_of_work(index, previous_hash.clone());
        let hash = Block::calculate_hash(index, &timestamp, proof, &previous_hash, &encoded_model);

        Block {
            index,
            timestamp,
            proof,
            hash,
            previous_hash,
            encoded_model
        }
    }

    fn calculate_hash(index: usize, timestamp: &str, proof: usize, previous_hash: &str, encoded_model: &str) -> String {
        let content = format!(
            "{}{}{}{}{}",
            index,
            timestamp,
            proof,
            previous_hash,
            encoded_model
        );

        let mut hasher = Hasher::new();
        hasher.update(content.as_bytes());
        let hash = hasher.finalize();
        hash.to_hex().to_string()
    }

    fn proof_of_work(index: usize, previous_hash: String) -> usize {
        let start_time = Instant::now();
        let mut proof = 0;

        while !Block::is_valid_proof(proof, index, &previous_hash) {
            proof += 1;
        }

        let elapsed_time = start_time.elapsed();
        println!("Proof-of-work completed in {} seconds.", elapsed_time.as_secs_f64());
        proof
    }

    fn is_valid_proof(proof: usize, index: usize, previous_hash: &String) -> bool {
        let guess = format!("{}{}", proof, Utc::now().timestamp_millis());
        let guess_hash = Block::calculate_hash(
            index,
            &Utc::now().to_rfc3339(),
            proof,
            &previous_hash,
            &guess
        );

        guess_hash.starts_with(&"0".repeat(DIFFICULTY))
    }

    fn to_json(&self) -> String {
        serde_json::to_string(self).unwrap()
    }

    fn from_json(json: &str) -> Block {
        serde_json::from_str(json).unwrap()
    }
}

impl Default for Block {
    fn default() -> Block {
        let index = 0;
        let timestamp = Utc::now().to_rfc3339();
        let proof = usize::default();
        let previous_hash = String::default();
        let encoded_model = String::default();

        let hash = Block::calculate_hash(index, &timestamp, proof, &previous_hash, &encoded_model);

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
    connection: Connection,
}

impl BlockChain {
    pub fn new() -> Result<Self, rusqlite::Error> {
        let connection = Connection::open("blockchain.db")?;
        connection.execute(
            "CREATE TABLE IF NOT EXISTS blocks (
                index INTEGER PRIMARY KEY,
                timestamp TIMESTAMP UNIQUE NOT NULL,
                proof INTEGER NOT NULL,
                hash TEXT UNIQUE NOT NULL,
                previous_hash TEXT UNIQUE NOT NULL,
                encoded_model TEXT NOT NULL
            )",
            []
        )?;

        let is_empty: bool = connection.query_row(
            "SELECT COUNT(*) FROM blocks",
            [],
            |row| row.get(0)
        )?;

        if is_empty {
            let block = Block::default();
            connection.execute(
                "INSERT INTO blocks (index, timestamp, proof, hash, previous_hash, encoded_model)
                VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
                params![
                    block.index,
                    &block.timestamp,
                    block.proof,
                    &block.hash,
                    &block.previous_hash,
                    &block.encoded_model,
                ],
            )?;
        }

        Ok(BlockChain { connection })
    }

    pub fn save_block(&self, block: &Block) -> Result<(), rusqlite::Error> {
        self.connection.execute(
            "INSERT INTO blocks (index, timestamp, proof, hash, previous_hash, encoded_model)
            VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
            params![
                block.index,
                &block.timestamp,
                block.proof,
                &block.hash,
                &block.previous_hash,
                &block.encoded_model
            ],
        )?;

        Ok(())
    }

    pub fn get_block_by_index(&self, index: usize) -> Result<Option<Block>, rusqlite::Error> {
        let mut smtm = self.connection.prepare(
            "SELECT index, timestamp, proof, hash, previous_hash, encoded_model
            FROM blocks WHERE index = ?1",
        )?;

        let result = smtm.query_row(params![index], |row| {
            Ok(Block {
                index: row.get(0)?,
                timestamp: row.get(1)?,
                proof: row.get(2)?,
                hash: row.get(3)?,
                previous_hash: row.get(4)?,
                encoded_model: row.get(5)?,
            }
                )
        });

        match result {
            Ok(block) => Ok(Some(block)),
            Err(rusqlite::Error::QueryReturnedNoRows) => Err(rusqlite::Error::QueryReturnedNoRows),
            Err(err) => Err(err)
        }
    }

    pub fn get_last_block(&self) -> Result<Option<Block>, rusqlite::Error> {
        let mut smtm = self.connection.prepare(
            "SELECT index, timestamp, proof, hash, previous_hash, encoded_model
            FROM blocks ORDER BY index DESC LIMIT 1",
        )?;

        let result = smtm.query_row([], |row| {
            Ok(Block {
                index: row.get(0)?,
                timestamp: row.get(1)?,
                proof: row.get(2)?,
                hash: row.get(3)?,
                previous_hash: row.get(4)?,
                encoded_model: row.get(5)?,
            }
                )
        });

        match result {
            Ok(block) => Ok(Some(block)),
            Err(rusqlite::Error::QueryReturnedNoRows) => Err(rusqlite::Error::QueryReturnedNoRows),
            Err(err) => Err(err)
        }
    }
}

#[no_mangle]
pub extern "C" fn init_blockchain() -> *mut BlockChain {
    Box::into_raw(Box::new(BlockChain::new().unwrap()))
}

#[no_mangle]
pub extern "C" fn add_block(chain: *mut BlockChain, encoded_model: *const i8) -> () {
    let chain = unsafe { &mut *chain };
    let encoded_model_string = unsafe { CStr::from_ptr(encoded_model).to_str().unwrap() };
    if let Ok(Some(last_block)) = chain.get_last_block() {
        let new_block = Block::new(
            last_block.index + 1,
            Utc::now().to_rfc3339(),
            last_block.hash.clone(),
            encoded_model_string.to_string(),
        );

        match chain.save_block(&new_block) {
            Ok(_) => println!("Block with index {} saved.", new_block.index),
            Err(err) => eprintln!("{}", err),
        }
    } else {
        eprintln!("Error getting last block.")
    }
}