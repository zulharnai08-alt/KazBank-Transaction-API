-- Task 4: run the commands in TWO separate psql sessions.
-- The order matters. Use existing account IDs 1 and 2.

-- SESSION A:
-- BEGIN;
-- SELECT account_id FROM accounts WHERE account_id = 1 FOR UPDATE;
-- (wait for Session B to lock account 2)
-- SELECT account_id FROM accounts WHERE account_id = 2 FOR UPDATE;

-- SESSION B:
-- BEGIN;
-- SELECT account_id FROM accounts WHERE account_id = 2 FOR UPDATE;
-- (after Session A is waiting on account 2, run the next command)
-- SELECT account_id FROM accounts WHERE account_id = 1 FOR UPDATE;

-- PostgreSQL should abort one session with: ERROR: deadlock detected
-- Run ROLLBACK; in both sessions afterward.
-- These SELECT ... FOR UPDATE statements do not modify balances.
