use core::time;
use chrono::{Utc, DateTime};
use blake3::Hasher;
use rusqlite::{params, Connection};
use serde::{Serialize, Deserialize};
use serde_json::json;

#[derive(Serialize, Deserialize, Debug)]
struct Block {
    index: usize,
    timestamp: String,
    proof: usize,
    hash: String,
    previous_hash: String,
    encoded_model: String,
}

impl Block {
    fn new(index: usize, timestamp: String, proof: usize, previous_hash: String, encoded_model: String) -> Self {
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

    fn calculate_hash(index: usize, timestamp: &String, proof: usize, previous_hash: &String, encoded_model: &String) -> String {
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
}