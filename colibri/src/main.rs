mod db;

fn main() {
    let database = db::handler::Database::new().unwrap();
    database.unlock();
    db::tasks::query_spam_transactions(&database);
}