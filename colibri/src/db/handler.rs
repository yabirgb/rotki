use rusqlite::Connection;
use simple_error::SimpleError;

pub struct Database {
    pub conn: Connection
}

impl Database {
    pub fn new() -> Result<Self, SimpleError>{
        let conn_setup = Connection::open("/Users/yabirgb/Library/Application Support/rotki/data/yabirgb/rotkehlchen.db");
        if conn_setup.is_err() {
            println!("Error opening test.db: {:?}", conn_setup.unwrap_err());
            return Err(SimpleError::new("Failed to initialize db connection"));
        }
        Ok(Database {
            conn: conn_setup.unwrap(),
        })
    }

    pub fn unlock(&self) -> Result<(), SimpleError>{
        if let Err(_) = self.conn.prepare(
            format!(r#"PRAGMA KEY="{}""#, r#"}~%-F9qs""TYQH$\/\lg-<:.XHev?=W"#).as_str()
        ) {
            return Err(SimpleError::new("Failed to unlock database"))
        }

        Ok(())
    }
    
}

