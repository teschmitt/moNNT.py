-- upgrade --
ALTER TABLE "newsgroup" ADD "default_subscribe" INT NOT NULL  DEFAULT 1;
ALTER TABLE "newsgroup" ADD "status" VARCHAR(1) NOT NULL  DEFAULT 'y';
-- downgrade --
ALTER TABLE "newsgroup" DROP COLUMN "default_subscribe";
ALTER TABLE "newsgroup" DROP COLUMN "status";
