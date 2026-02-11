-- Migration v84: enforce component DB boundary in octopusos database
--
-- Purpose:
-- 1) Remove tables that belong to other component databases.
-- 2) Keep OctopusOS DB as the single source of octopus-owned schema only.

-- MemoryOS-owned table must not exist in octopusos DB.
DROP TABLE IF EXISTS memory_proposals;

