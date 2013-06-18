-- NOTE: Currently some (few) tests depend on this test data but
-- ideally we should get rid of this SQL file and use helper methods
-- and testdb.FakeDataMixin in test cases.

PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE push_pushes (
	id INTEGER NOT NULL,
	title VARCHAR,
	user VARCHAR,
	branch VARCHAR,
	revision VARCHAR(40),
	state VARCHAR,
	created INTEGER,
	modified INTEGER,
	pushtype VARCHAR,
	extra_pings VARCHAR,
	PRIMARY KEY (id)
);
INSERT INTO "push_pushes" VALUES(
       1,
       'Test Push',
       'bmetin',
       'deploy-test',
       '0000000000000000000000000000000000000000',
       'accepting',
       1346458516.87736,
       1346458516.87736,
       'regular',
       NULL
);
INSERT INTO "push_pushes" VALUES(2,
       'Second Push',
       'bmetin',
       'deploy-second',
       '0000000000000000000000000000000000000000',
       'accepting',
       1346458663.2721,
       1346458663.2721,
       'private',
       NULL
);
CREATE TABLE push_pushcontents (
	request INTEGER NOT NULL,
	push INTEGER NOT NULL,
	PRIMARY KEY (request, push)
);
INSERT INTO "push_pushcontents" VALUES(1,1);
CREATE TABLE push_plans (
	id INTEGER NOT NULL,
	content VARCHAR,
	path VARCHAR,
	PRIMARY KEY (id)
);
CREATE TABLE push_requests (
	id INTEGER NOT NULL,
	user VARCHAR,
	state VARCHAR,
	repo VARCHAR,
	branch VARCHAR,
	revision VARCHAR(40),
	tags VARCHAR,
	created INTEGER,
	modified INTEGER,
	title VARCHAR,
	comments VARCHAR,
	reviewid INTEGER,
	description VARCHAR,
	watchers VARCHAR,
	PRIMARY KEY (id)
);
INSERT INTO "push_requests" VALUES(1,
       'bmetin',
       'pickme',
       'bmetin',
       'bmetin_fix_stuff',
       '0000000000000000000000000000000000000000',
       'buildbot,images',
       1346458591.51592,
       1346458591.51592,
       'Fix stuff',
       '',
       NULL,
       'Ship it! from someone.

This branch fixes stuff.',
       NULL
);
INSERT INTO "push_requests" VALUES(2,
       'bmetin',
       'requested',
       'bmetin',
       'bmetin_important_fixes',
       '0000000000000000000000000000000000000000',
       'buildbot,plans,special,urgent',
       1346458626.04348,
       1346458626.04348,
       'More fixes for important things',
       '',
       123,
       'no comment',
       NULL
);
INSERT INTO "push_requests" VALUES(3,
       'otheruser',
       'requested',
       'testuser',
       'testuser_important_fixes',
       '0000000000000000000000000000000000000000',
       'buildbot',
       1346458626.04355,
       1346458655.04348,
       '',
       '',
       456,
       '',
       NULL
);
CREATE TABLE push_checklist (
	id INTEGER NOT NULL,
	request INTEGER NOT NULL,
	type VARCHAR(50),
	complete SMALLINT NOT NULL,
	target VARCHAR(50),
	PRIMARY KEY (id)
);
INSERT INTO "push_checklist" VALUES(1,2,'plans',0,'stage');
INSERT INTO "push_checklist" VALUES(2,2,'plans',0,'prod');
CREATE TABLE push_removals (
	id INTEGER NOT NULL,
	request INTEGER NOT NULL,
	push INTEGER NOT NULL,
	reason VARCHAR,
	pushmaster VARCHAR,
	timestamp INTEGER NOT NULL,
	PRIMARY KEY (id)
);
COMMIT;
