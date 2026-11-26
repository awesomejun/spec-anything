-- Extracted directly from live PocketBase v0.40.6 pb_data/data.db

CREATE TABLE `_authOrigins` (`collectionRef` TEXT DEFAULT '' NOT NULL, `created` TEXT DEFAULT '' NOT NULL, `fingerprint` TEXT DEFAULT '' NOT NULL, `id` TEXT PRIMARY KEY DEFAULT ('r'||lower(hex(randomblob(7)))) NOT NULL, `recordRef` TEXT DEFAULT '' NOT NULL, `updated` TEXT DEFAULT '' NOT NULL);

CREATE TABLE `_collections` (
				`id`         TEXT PRIMARY KEY DEFAULT ('r'||lower(hex(randomblob(7)))) NOT NULL,
				`system`     BOOLEAN DEFAULT FALSE NOT NULL,
				`type`       TEXT DEFAULT "base" NOT NULL,
				`name`       TEXT UNIQUE NOT NULL,
				`fields`     JSON DEFAULT "[]" NOT NULL,
				`indexes`    JSON DEFAULT "[]" NOT NULL,
				`listRule`   TEXT DEFAULT NULL,
				`viewRule`   TEXT DEFAULT NULL,
				`createRule` TEXT DEFAULT NULL,
				`updateRule` TEXT DEFAULT NULL,
				`deleteRule` TEXT DEFAULT NULL,
				`options`    JSON DEFAULT "{}" NOT NULL,
				`created`    TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%fZ')) NOT NULL,
				`updated`    TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%fZ')) NOT NULL
			);

CREATE TABLE `_externalAuths` (`collectionRef` TEXT DEFAULT '' NOT NULL, `created` TEXT DEFAULT '' NOT NULL, `id` TEXT PRIMARY KEY DEFAULT ('r'||lower(hex(randomblob(7)))) NOT NULL, `provider` TEXT DEFAULT '' NOT NULL, `providerId` TEXT DEFAULT '' NOT NULL, `recordRef` TEXT DEFAULT '' NOT NULL, `updated` TEXT DEFAULT '' NOT NULL);

CREATE TABLE `_mfas` (`collectionRef` TEXT DEFAULT '' NOT NULL, `created` TEXT DEFAULT '' NOT NULL, `id` TEXT PRIMARY KEY DEFAULT ('r'||lower(hex(randomblob(7)))) NOT NULL, `method` TEXT DEFAULT '' NOT NULL, `recordRef` TEXT DEFAULT '' NOT NULL, `updated` TEXT DEFAULT '' NOT NULL);

CREATE TABLE `_migrations` (file VARCHAR(255) PRIMARY KEY NOT NULL, applied INTEGER NOT NULL);

CREATE TABLE `_otps` (`collectionRef` TEXT DEFAULT '' NOT NULL, `created` TEXT DEFAULT '' NOT NULL, `id` TEXT PRIMARY KEY DEFAULT ('r'||lower(hex(randomblob(7)))) NOT NULL, `password` TEXT DEFAULT '' NOT NULL, `recordRef` TEXT DEFAULT '' NOT NULL, `sentTo` TEXT DEFAULT '' NOT NULL, `updated` TEXT DEFAULT '' NOT NULL);

CREATE TABLE `_params` (
			`id`      TEXT PRIMARY KEY DEFAULT ('r'||lower(hex(randomblob(7)))) NOT NULL,
			`value`   JSON DEFAULT NULL,
			`created` TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%fZ')) NOT NULL,
			`updated` TEXT DEFAULT (strftime('%Y-%m-%d %H:%M:%fZ')) NOT NULL
		);

CREATE TABLE `_superusers` (`created` TEXT DEFAULT '' NOT NULL, `email` TEXT DEFAULT '' NOT NULL, `emailVisibility` BOOLEAN DEFAULT FALSE NOT NULL, `id` TEXT PRIMARY KEY DEFAULT ('r'||lower(hex(randomblob(7)))) NOT NULL, `password` TEXT DEFAULT '' NOT NULL, `tokenKey` TEXT DEFAULT '' NOT NULL, `updated` TEXT DEFAULT '' NOT NULL, `verified` BOOLEAN DEFAULT FALSE NOT NULL);

CREATE TABLE `articles` (`id` TEXT PRIMARY KEY DEFAULT ('r'||lower(hex(randomblob(7)))) NOT NULL, `published` BOOLEAN DEFAULT FALSE NOT NULL, `slug` TEXT DEFAULT '' NOT NULL, `title` TEXT DEFAULT '' NOT NULL, `views` NUMERIC DEFAULT 0 NOT NULL);

CREATE TABLE `users` (`avatar` TEXT DEFAULT '' NOT NULL, `created` TEXT DEFAULT '' NOT NULL, `email` TEXT DEFAULT '' NOT NULL, `emailVisibility` BOOLEAN DEFAULT FALSE NOT NULL, `id` TEXT PRIMARY KEY DEFAULT ('r'||lower(hex(randomblob(7)))) NOT NULL, `name` TEXT DEFAULT '' NOT NULL, `password` TEXT DEFAULT '' NOT NULL, `tokenKey` TEXT DEFAULT '' NOT NULL, `updated` TEXT DEFAULT '' NOT NULL, `verified` BOOLEAN DEFAULT FALSE NOT NULL);

CREATE INDEX idx__collections_type on `_collections` (`type`);

CREATE UNIQUE INDEX `idx_articles_slug` ON `articles` (`slug`);

CREATE UNIQUE INDEX `idx_authOrigins_unique_pairs` ON `_authOrigins` (
  `collectionRef`,
  `recordRef`,
  `fingerprint`
);

CREATE UNIQUE INDEX `idx_email__pb_users_auth_` ON `users` (`email`) WHERE `email` != '';

CREATE UNIQUE INDEX `idx_email_pbc_3142635823` ON `_superusers` (`email`) WHERE `email` != '';

CREATE UNIQUE INDEX `idx_externalAuths_collection_provider` ON `_externalAuths` (
  `collectionRef`,
  `provider`,
  `providerId`
);

CREATE UNIQUE INDEX `idx_externalAuths_record_provider` ON `_externalAuths` (
  `collectionRef`,
  `recordRef`,
  `provider`
);

CREATE INDEX `idx_mfas_collectionRef_recordRef` ON `_mfas` (
  `collectionRef`,
  `recordRef`
);

CREATE INDEX `idx_otps_collectionRef_recordRef` ON `_otps` (
  `collectionRef`,
  `recordRef`
);

CREATE UNIQUE INDEX `idx_tokenKey__pb_users_auth_` ON `users` (`tokenKey`);

CREATE UNIQUE INDEX `idx_tokenKey_pbc_3142635823` ON `_superusers` (`tokenKey`);
