-- upgrade --
CREATE TABLE IF NOT EXISTS "newsgroup" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "status" VARCHAR(1) NOT NULL  DEFAULT 'y',
    "default_subscribe" INT NOT NULL  DEFAULT 1,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "message" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "from" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "subject" VARCHAR(255) NOT NULL,
    "message_id" VARCHAR(255) NOT NULL,
    "path" TEXT NOT NULL,
    "references" TEXT,
    "reply_to" VARCHAR(255),
    "organization" VARCHAR(255),
    "x_ref" VARCHAR(255),
    "user_agent" VARCHAR(255),
    "body" TEXT NOT NULL,
    "newsgroup_id" INT NOT NULL REFERENCES "newsgroup" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(20) NOT NULL,
    "content" JSON NOT NULL
);
