use anyhow::Result;
use clap::Parser;
use fs2::FileExt;
use rusqlite::{params, Connection};
use std::fmt;
use std::fs::{self, File, OpenOptions};
use std::path::{Path, PathBuf};
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

#[derive(Parser, Debug)]
#[command(about = "Rust writer that coordinates with Python via a lock file", version)]
struct Args {
    /// Name written into the shared table
    #[arg(long, default_value = "rust")]
    name: String,
    /// Number of iterations to perform
    #[arg(long, default_value_t = 8)]
    iterations: u32,
    /// Delay between iterations, in milliseconds
    #[arg(long = "delay-ms", default_value_t = 1_000)]
    delay_ms: u64,
}

struct MessageRow {
    id: i64,
    source: String,
    iteration: i64,
}

impl fmt::Display for MessageRow {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "#{}:{}@{}", self.id, self.source, self.iteration)
    }
}

fn main() -> Result<()> {
    let args = Args::parse();
    let base_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    fs::create_dir_all(&base_dir)?;
    let db_path = base_dir.join("demo.db");
    let lock_path = base_dir.join("demo.db.lock");
    let lock_file = open_lock_file(&lock_path)?;
    let conn = open_database(&db_path)?;

    for iteration in 0..args.iterations {
        with_file_lock(&lock_file, || write_row(&conn, &args.name, iteration))?;
        let rows = read_recent(&conn, 5)?;
        let joined = rows
            .iter()
            .map(ToString::to_string)
            .collect::<Vec<_>>()
            .join(", ");
        println!(
            "[{}] inserted iteration {}. Recent rows: {}",
            args.name, iteration, joined
        );
        thread::sleep(Duration::from_millis(args.delay_ms));
    }

    Ok(())
}

fn with_file_lock<F>(lock_file: &File, action: F) -> Result<()>
where
    F: FnOnce() -> Result<()>,
{
    lock_file.lock_exclusive()?;
    let action_result = action();
    let unlock_result = lock_file.unlock();
    action_result?;
    unlock_result?;
    Ok(())
}

fn open_lock_file(lock_path: &Path) -> Result<File> {
    let file = OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .open(lock_path)?;
    Ok(file)
}

fn write_row(conn: &Connection, source: &str, iteration: u32) -> Result<()> {
    let ts = SystemTime::now()
        .duration_since(UNIX_EPOCH)?
        .as_secs_f64();
    conn.execute(
        "INSERT INTO messages (source, iteration, inserted_at) VALUES (?1, ?2, ?3)",
        params![source, iteration as i64, ts],
    )?;
    Ok(())
}

fn read_recent(conn: &Connection, limit: usize) -> Result<Vec<MessageRow>> {
    let mut stmt = conn.prepare(
        "SELECT id, source, iteration FROM messages ORDER BY id DESC LIMIT ?1",
    )?;
    let rows = stmt
        .query_map([limit as i64], |row| {
            Ok(MessageRow {
                id: row.get(0)?,
                source: row.get(1)?,
                iteration: row.get(2)?,
            })
        })?
        .collect::<rusqlite::Result<Vec<_>>>()?;
    Ok(rows)
}

fn open_database(db_path: &Path) -> Result<Connection> {
    let conn = Connection::open(db_path)?;
    conn.pragma_update(None, "journal_mode", "WAL")?;
    conn.execute(
        r#"
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                iteration INTEGER NOT NULL,
                inserted_at REAL NOT NULL
            )
        "#,
        [],
    )?;
    Ok(conn)
}
