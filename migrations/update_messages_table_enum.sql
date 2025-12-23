-- Create new enum
CREATE TYPE grade_level_new AS ENUM (
  'grade_6_8',
  'grade_9_11',
  'grade_12_13',
  'university'
);

-- Update column
ALTER TABLE messages
ALTER COLUMN grade_level TYPE grade_level_new
USING grade_level::text::grade_level_new;

-- Drop old enum
DROP TYPE grade_level;

-- Rename new enum
ALTER TYPE grade_level_new RENAME TO grade_level;
