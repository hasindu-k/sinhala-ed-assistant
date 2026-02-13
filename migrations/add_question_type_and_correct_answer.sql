-- Add question_type and correct_answer to questions and sub_questions
ALTER TABLE questions ADD COLUMN question_type VARCHAR;
ALTER TABLE questions ADD COLUMN correct_answer VARCHAR;

ALTER TABLE sub_questions ADD COLUMN question_type VARCHAR;
ALTER TABLE sub_questions ADD COLUMN correct_answer VARCHAR;
