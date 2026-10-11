-- =============================================================================
-- SmartHire AI — PostgreSQL Schema
-- =============================================================================
-- Instructions:
--   1. Open pgAdmin or psql
--   2. Create a database named: smarthire
--      (In pgAdmin: right-click Databases > Create > name it smarthire > Save)
--   3. Click on the smarthire database, open Query Tool (Tools > Query Tool)
--   4. Paste this entire file and press F5 to run
-- =============================================================================


-- =============================================================================
-- EXTENSIONS
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- =============================================================================
-- DROP existing types if re-running (safe re-run support)
-- =============================================================================
DROP TYPE IF EXISTS user_role          CASCADE;
DROP TYPE IF EXISTS employment_type    CASCADE;
DROP TYPE IF EXISTS exp_level          CASCADE;
DROP TYPE IF EXISTS job_status         CASCADE;
DROP TYPE IF EXISTS application_status CASCADE;
DROP TYPE IF EXISTS roadmap_status     CASCADE;
DROP TYPE IF EXISTS interview_status   CASCADE;
DROP TYPE IF EXISTS question_type      CASCADE;
DROP TYPE IF EXISTS difficulty_level   CASCADE;
DROP TYPE IF EXISTS interview_exp_level CASCADE;
DROP TYPE IF EXISTS notification_type  CASCADE;
DROP TYPE IF EXISTS message_role       CASCADE;


-- =============================================================================
-- DROP existing tables (clean slate — safe re-run)
-- Order matters: child tables first, then parents
-- =============================================================================
DROP TABLE IF EXISTS chat_messages          CASCADE;
DROP TABLE IF EXISTS chat_sessions          CASCADE;
DROP TABLE IF EXISTS documents              CASCADE;
DROP TABLE IF EXISTS notifications          CASCADE;
DROP TABLE IF EXISTS saved_jobs             CASCADE;
DROP TABLE IF EXISTS interview_evaluations  CASCADE;
DROP TABLE IF EXISTS interview_answers      CASCADE;
DROP TABLE IF EXISTS interview_questions    CASCADE;
DROP TABLE IF EXISTS interviews             CASCADE;
DROP TABLE IF EXISTS learning_roadmaps      CASCADE;
DROP TABLE IF EXISTS skill_gaps             CASCADE;
DROP TABLE IF EXISTS match_scores           CASCADE;
DROP TABLE IF EXISTS applications           CASCADE;
DROP TABLE IF EXISTS job_skills             CASCADE;
DROP TABLE IF EXISTS jobs                   CASCADE;
DROP TABLE IF EXISTS candidate_skills       CASCADE;
DROP TABLE IF EXISTS skills                 CASCADE;
DROP TABLE IF EXISTS resumes                CASCADE;
DROP TABLE IF EXISTS recruiter_profiles     CASCADE;
DROP TABLE IF EXISTS candidate_profiles     CASCADE;
DROP TABLE IF EXISTS users                  CASCADE;


-- =============================================================================
-- ENUMS
-- =============================================================================
CREATE TYPE user_role AS ENUM (
    'CANDIDATE', 'RECRUITER', 'ADMIN'
);

CREATE TYPE employment_type AS ENUM (
    'FULL_TIME', 'PART_TIME', 'CONTRACT', 'INTERNSHIP', 'FREELANCE'
);

CREATE TYPE exp_level AS ENUM (
    'FRESHER', 'JUNIOR', 'MID', 'SENIOR', 'LEAD', 'MANAGER'
);

CREATE TYPE job_status AS ENUM (
    'DRAFT', 'ACTIVE', 'CLOSED', 'PAUSED'
);

CREATE TYPE application_status AS ENUM (
    'APPLIED', 'UNDER_REVIEW', 'SHORTLISTED',
    'INTERVIEW_SCHEDULED', 'REJECTED', 'WITHDRAWN', 'OFFERED'
);

CREATE TYPE roadmap_status AS ENUM (
    'PENDING', 'GENERATED', 'IN_PROGRESS', 'COMPLETED'
);

CREATE TYPE interview_status AS ENUM (
    'PENDING', 'IN_PROGRESS', 'COMPLETED', 'EVALUATED'
);

CREATE TYPE question_type AS ENUM (
    'TECHNICAL', 'CODING', 'BEHAVIORAL', 'PROJECT'
);

CREATE TYPE difficulty_level AS ENUM (
    'EASY', 'MEDIUM', 'HARD'
);

CREATE TYPE interview_exp_level AS ENUM (
    'FRESHER', 'JUNIOR', 'MID', 'SENIOR'
);

CREATE TYPE notification_type AS ENUM (
    'APPLICATION_UPDATE', 'NEW_JOB_MATCH',
    'INTERVIEW_REMINDER', 'PROFILE_INCOMPLETE', 'SYSTEM'
);

CREATE TYPE message_role AS ENUM (
    'USER', 'ASSISTANT', 'SYSTEM'
);


-- =============================================================================
-- TABLE: users
-- NOTE: 'role' is a reserved keyword in PostgreSQL — using user_role column name
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id                  SERIAL          PRIMARY KEY,
    email               VARCHAR(255)    NOT NULL UNIQUE,
    hashed_password     VARCHAR(255)    NOT NULL,
    full_name           VARCHAR(255)    NOT NULL,
    user_role           user_role       NOT NULL,
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    is_verified         BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email     ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_user_role ON users(user_role);


-- =============================================================================
-- TABLE: candidate_profiles
-- =============================================================================
CREATE TABLE IF NOT EXISTS candidate_profiles (
    id                      SERIAL          PRIMARY KEY,
    user_id                 INT             NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    phone                   VARCHAR(20),
    location                VARCHAR(255),
    linkedin_url            VARCHAR(512),
    github_url              VARCHAR(512),
    portfolio_url           VARCHAR(512),
    bio                     TEXT,
    -- Education
    degree                  VARCHAR(255),
    branch                  VARCHAR(255),
    institution             VARCHAR(255),
    cgpa                    NUMERIC(4,2),
    graduation_year         INT,
    -- Experience
    years_of_experience     NUMERIC(4,1)    DEFAULT 0,
    current_company         VARCHAR(255),
    current_job_title       VARCHAR(255),
    -- Career preferences
    target_roles            JSONB           DEFAULT '[]',
    preferred_locations     JSONB           DEFAULT '[]',
    expected_salary         VARCHAR(100),
    -- Scores
    profile_completion_pct  INT             DEFAULT 0,
    resume_ats_score        INT,
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_candidate_profiles_user_id ON candidate_profiles(user_id);


-- =============================================================================
-- TABLE: recruiter_profiles
-- =============================================================================
CREATE TABLE IF NOT EXISTS recruiter_profiles (
    id                   SERIAL          PRIMARY KEY,
    user_id              INT             NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    company_name         VARCHAR(255),
    company_website      VARCHAR(512),
    company_size         VARCHAR(100),
    industry             VARCHAR(255),
    company_location     VARCHAR(255),
    company_description  TEXT,
    phone                VARCHAR(20),  
    job_title            VARCHAR(255),
    linkedin_url         VARCHAR(512),
    created_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recruiter_profiles_user_id ON recruiter_profiles(user_id);


-- =============================================================================
-- TABLE: resumes
-- =============================================================================
CREATE TABLE IF NOT EXISTS resumes (
    id                  SERIAL          PRIMARY KEY,
    user_id             INT             NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    original_filename   VARCHAR(255)    NOT NULL,
    stored_filename     VARCHAR(255)    NOT NULL,
    file_path           VARCHAR(512)    NOT NULL,
    file_size_bytes     INT,
    mime_type           VARCHAR(100)    DEFAULT 'application/pdf',
    raw_text            TEXT,
    extracted_sections  JSONB,
    parsed_data         JSONB,
    is_parsed           BOOLEAN         NOT NULL DEFAULT FALSE,
    parse_error         TEXT,
    is_active           BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resumes_user_id   ON resumes(user_id);
CREATE INDEX IF NOT EXISTS idx_resumes_is_active ON resumes(is_active);


-- =============================================================================
-- TABLE: skills  (master skill taxonomy)
-- NOTE: 'name' can conflict — using skill_name to be safe
-- =============================================================================
CREATE TABLE IF NOT EXISTS skills (
    id          SERIAL          PRIMARY KEY,
    skill_name  VARCHAR(100)    NOT NULL UNIQUE,
    category    VARCHAR(100)    NOT NULL,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_skills_skill_name ON skills(skill_name);
CREATE INDEX IF NOT EXISTS idx_skills_category   ON skills(category);


-- =============================================================================
-- TABLE: candidate_skills
-- =============================================================================
CREATE TABLE IF NOT EXISTS candidate_skills (
    id                      SERIAL          PRIMARY KEY,
    candidate_profile_id    INT             NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    skill_id                INT             NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    proficiency_level       VARCHAR(50),
    years_used              NUMERIC(4,1),
    skill_source            VARCHAR(50)     NOT NULL DEFAULT 'ai_extracted',
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_candidate_skill UNIQUE (candidate_profile_id, skill_id)
);

CREATE INDEX IF NOT EXISTS idx_candidate_skills_profile ON candidate_skills(candidate_profile_id);
CREATE INDEX IF NOT EXISTS idx_candidate_skills_skill   ON candidate_skills(skill_id);


-- =============================================================================
-- TABLE: jobs
-- =============================================================================
CREATE TABLE IF NOT EXISTS jobs (
    id                              SERIAL              PRIMARY KEY,
    recruiter_profile_id            INT                 NOT NULL REFERENCES recruiter_profiles(id) ON DELETE CASCADE,
    title                           VARCHAR(255)        NOT NULL,
    company                         VARCHAR(255)        NOT NULL,
    location                        VARCHAR(255),
    is_remote                       BOOLEAN             NOT NULL DEFAULT FALSE,
    employment_type                 employment_type     NOT NULL DEFAULT 'FULL_TIME',
    experience_level                exp_level           NOT NULL DEFAULT 'MID',
    salary_min                      VARCHAR(50),
    salary_max                      VARCHAR(50),
    salary_currency                 VARCHAR(10)         DEFAULT 'USD',
    description                     TEXT                NOT NULL,
    responsibilities                TEXT,
    education_requirements          TEXT,
    ai_extracted_required_skills    JSONB               DEFAULT '[]',
    ai_extracted_preferred_skills   JSONB               DEFAULT '[]',
    ai_extracted_experience_years   VARCHAR(50),
    ai_extracted_tools              JSONB               DEFAULT '[]',
    ai_extracted_technologies       JSONB               DEFAULT '[]',
    job_status                      job_status          NOT NULL DEFAULT 'DRAFT',
    views_count                     INT                 NOT NULL DEFAULT 0,
    created_at                      TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jobs_recruiter   ON jobs(recruiter_profile_id);
CREATE INDEX IF NOT EXISTS idx_jobs_job_status  ON jobs(job_status);
CREATE INDEX IF NOT EXISTS idx_jobs_title       ON jobs(title);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at  ON jobs(created_at DESC);


-- =============================================================================
-- TABLE: job_skills
-- =============================================================================
CREATE TABLE IF NOT EXISTS job_skills (
    id          SERIAL          PRIMARY KEY,
    job_id      INT             NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id    INT             NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    is_required BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_job_skills_job   ON job_skills(job_id);
CREATE INDEX IF NOT EXISTS idx_job_skills_skill ON job_skills(skill_id);


-- =============================================================================
-- TABLE: applications
-- =============================================================================
CREATE TABLE IF NOT EXISTS applications (
    id                      SERIAL              PRIMARY KEY,
    candidate_profile_id    INT                 NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    job_id                  INT                 NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    app_status              application_status  NOT NULL DEFAULT 'APPLIED',
    cover_letter            TEXT,
    recruiter_notes         TEXT,
    applied_at              TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_application UNIQUE (candidate_profile_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_applications_candidate ON applications(candidate_profile_id);
CREATE INDEX IF NOT EXISTS idx_applications_job       ON applications(job_id);
CREATE INDEX IF NOT EXISTS idx_applications_status    ON applications(app_status);


-- =============================================================================
-- TABLE: match_scores
-- =============================================================================
CREATE TABLE IF NOT EXISTS match_scores (
    id                          SERIAL          PRIMARY KEY,
    candidate_profile_id        INT             NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    job_id                      INT             NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    overall_score               NUMERIC(5,2)    NOT NULL,
    skill_match_score           NUMERIC(5,2),
    semantic_similarity_score   NUMERIC(5,2),
    experience_match_score      NUMERIC(5,2),
    education_match_score       NUMERIC(5,2),
    tfidf_score                 NUMERIC(5,4),
    ml_rank_score               NUMERIC(5,2),
    explanation                 JSONB,
    created_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_match_score UNIQUE (candidate_profile_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_match_scores_candidate ON match_scores(candidate_profile_id);
CREATE INDEX IF NOT EXISTS idx_match_scores_job       ON match_scores(job_id);
CREATE INDEX IF NOT EXISTS idx_match_scores_overall   ON match_scores(overall_score DESC);


-- =============================================================================
-- TABLE: skill_gaps
-- =============================================================================
CREATE TABLE IF NOT EXISTS skill_gaps (
    id                      SERIAL          PRIMARY KEY,
    candidate_profile_id    INT             NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    job_id                  INT             NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    matched_skills          JSONB           DEFAULT '[]',
    missing_skills          JSONB           DEFAULT '[]',
    partial_skills          JSONB           DEFAULT '[]',
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_skill_gap UNIQUE (candidate_profile_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_skill_gaps_candidate ON skill_gaps(candidate_profile_id);
CREATE INDEX IF NOT EXISTS idx_skill_gaps_job       ON skill_gaps(job_id);


-- =============================================================================
-- TABLE: learning_roadmaps
-- =============================================================================
CREATE TABLE IF NOT EXISTS learning_roadmaps (
    id                      SERIAL          PRIMARY KEY,
    candidate_profile_id    INT             NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    target_role             VARCHAR(255)    NOT NULL,
    missing_skills          JSONB           DEFAULT '[]',
    roadmap_data            JSONB           DEFAULT '[]',
    total_weeks             INT,
    roadmap_status          roadmap_status  NOT NULL DEFAULT 'PENDING',
    generation_error        TEXT,
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_roadmaps_candidate ON learning_roadmaps(candidate_profile_id);


-- =============================================================================
-- TABLE: interviews
-- =============================================================================
CREATE TABLE IF NOT EXISTS interviews (
    id                      SERIAL              PRIMARY KEY,
    candidate_profile_id    INT                 NOT NULL REFERENCES candidate_profiles(id) ON DELETE CASCADE,
    target_role             VARCHAR(255)        NOT NULL,
    experience_level        interview_exp_level NOT NULL DEFAULT 'FRESHER',
    difficulty              difficulty_level    NOT NULL DEFAULT 'MEDIUM',
    total_questions         INT                 NOT NULL DEFAULT 10,
    interview_status        interview_status    NOT NULL DEFAULT 'PENDING',
    technical_score         NUMERIC(5,2),
    communication_score     NUMERIC(5,2),
    overall_score           NUMERIC(5,2),
    created_at              TIMESTAMPTZ         NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_interviews_candidate ON interviews(candidate_profile_id);
CREATE INDEX IF NOT EXISTS idx_interviews_status    ON interviews(interview_status);


-- =============================================================================
-- TABLE: interview_questions
-- =============================================================================
CREATE TABLE IF NOT EXISTS interview_questions (
    id                  SERIAL              PRIMARY KEY,
    interview_id        INT                 NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    question_number     INT                 NOT NULL,
    question_text       TEXT                NOT NULL,
    question_type       question_type,
    difficulty          difficulty_level,
    expected_topics     JSONB               DEFAULT '[]',
    created_at          TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_iq_interview ON interview_questions(interview_id);


-- =============================================================================
-- TABLE: interview_answers
-- =============================================================================
CREATE TABLE IF NOT EXISTS interview_answers (
    id                      SERIAL          PRIMARY KEY,
    question_id             INT             NOT NULL UNIQUE REFERENCES interview_questions(id) ON DELETE CASCADE,
    answer_text             TEXT            NOT NULL,
    time_taken_seconds      INT,
    technical_correctness   NUMERIC(4,2),
    relevance_score         NUMERIC(4,2),
    completeness_score      NUMERIC(4,2),
    communication_score     NUMERIC(4,2),
    missing_concepts        JSONB           DEFAULT '[]',
    feedback                TEXT,
    submitted_at            TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ia_question ON interview_answers(question_id);


-- =============================================================================
-- TABLE: interview_evaluations
-- =============================================================================
CREATE TABLE IF NOT EXISTS interview_evaluations (
    id                  SERIAL          PRIMARY KEY,
    interview_id        INT             NOT NULL UNIQUE REFERENCES interviews(id) ON DELETE CASCADE,
    technical_score     NUMERIC(5,2)    NOT NULL,
    communication_score NUMERIC(5,2)    NOT NULL,
    overall_score       NUMERIC(5,2)    NOT NULL,
    strengths           JSONB           DEFAULT '[]',
    weaknesses          JSONB           DEFAULT '[]',
    recommended_topics  JSONB           DEFAULT '[]',
    summary             TEXT,
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);


-- =============================================================================
-- TABLE: saved_jobs
-- =============================================================================
CREATE TABLE IF NOT EXISTS saved_jobs (
    id          SERIAL          PRIMARY KEY,
    user_id     INT             NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id      INT             NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    saved_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_saved_job UNIQUE (user_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_saved_jobs_user ON saved_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_saved_jobs_job  ON saved_jobs(job_id);


-- =============================================================================
-- TABLE: notifications
-- NOTE: 'type' is not reserved but renaming to notif_type to be safe
-- =============================================================================
CREATE TABLE IF NOT EXISTS notifications (
    id          SERIAL              PRIMARY KEY,
    user_id     INT                 NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notif_type  notification_type   NOT NULL,
    title       VARCHAR(255)        NOT NULL,
    message     TEXT                NOT NULL,
    is_read     BOOLEAN             NOT NULL DEFAULT FALSE,
    extra_data  JSONB,
    created_at  TIMESTAMPTZ         NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user    ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);


-- =============================================================================
-- TABLE: documents  (RAG knowledge base)
-- =============================================================================
CREATE TABLE IF NOT EXISTS documents (
    id              SERIAL          PRIMARY KEY,
    doc_title       VARCHAR(255)    NOT NULL,
    doc_source      VARCHAR(512),
    content         TEXT            NOT NULL,
    doc_type        VARCHAR(100)    NOT NULL,
    is_embedded     BOOLEAN         NOT NULL DEFAULT FALSE,
    embedding_model VARCHAR(100),
    content_hash    VARCHAR(64),
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documents_doc_type    ON documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_documents_is_embedded ON documents(is_embedded);


-- =============================================================================
-- TABLE: chat_sessions
-- =============================================================================
CREATE TABLE IF NOT EXISTS chat_sessions (
    id          SERIAL          PRIMARY KEY,
    user_id     INT             NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       VARCHAR(255),
    is_active   BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id);


-- =============================================================================
-- TABLE: chat_messages
-- NOTE: 'role' is reserved — using msg_role
-- =============================================================================
CREATE TABLE IF NOT EXISTS chat_messages (
    id          SERIAL          PRIMARY KEY,
    session_id  INT             NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    msg_role    message_role    NOT NULL,
    content     TEXT            NOT NULL,
    sources     JSONB           DEFAULT '[]',
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session    ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);


-- =============================================================================
-- AUTO-UPDATE updated_at TRIGGER
-- =============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOREACH tbl IN ARRAY ARRAY[
        'users', 'candidate_profiles', 'recruiter_profiles', 'resumes',
        'candidate_skills', 'jobs', 'applications', 'match_scores',
        'skill_gaps', 'learning_roadmaps', 'interviews',
        'documents', 'chat_sessions'
    ]
    LOOP
        EXECUTE format(
            'CREATE OR REPLACE TRIGGER trg_%s_updated_at
             BEFORE UPDATE ON %I
             FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();',
            tbl, tbl
        );
    END LOOP;
END;
$$;


-- =============================================================================
-- SEED: Skill Taxonomy
-- =============================================================================
INSERT INTO skills (skill_name, category) VALUES
    -- Programming Languages
    ('Python',              'programming_language'),
    ('JavaScript',          'programming_language'),
    ('TypeScript',          'programming_language'),
    ('Java',                'programming_language'),
    ('C++',                 'programming_language'),
    ('C',                   'programming_language'),
    ('Go',                  'programming_language'),
    ('Rust',                'programming_language'),
    ('R',                   'programming_language'),
    ('SQL',                 'programming_language'),
    ('Bash',                'programming_language'),
    -- ML / AI
    ('Machine Learning',    'ml'),
    ('Deep Learning',       'ml'),
    ('NLP',                 'ml'),
    ('Computer Vision',     'ml'),
    ('Scikit-learn',        'ml'),
    ('TensorFlow',          'ml'),
    ('PyTorch',             'ml'),
    ('XGBoost',             'ml'),
    ('LightGBM',            'ml'),
    ('Keras',               'ml'),
    ('SHAP',                'ml'),
    ('Pandas',              'ml'),
    ('NumPy',               'ml'),
    ('Matplotlib',          'ml'),
    ('Seaborn',             'ml'),
    -- GenAI / RAG
    ('LLM',                 'genai'),
    ('RAG',                 'genai'),
    ('LangChain',           'genai'),
    ('LlamaIndex',          'genai'),
    ('Transformers',        'genai'),
    ('Embeddings',          'genai'),
    ('Prompt Engineering',  'genai'),
    ('FAISS',               'genai'),
    ('ChromaDB',            'genai'),
    ('OpenAI API',          'genai'),
    -- Frameworks (Backend)
    ('FastAPI',             'framework'),
    ('Flask',               'framework'),
    ('Django',              'framework'),
    ('Spring Boot',         'framework'),
    ('Node.js',             'framework'),
    ('Express.js',          'framework'),
    -- Frameworks (Frontend)
    ('React',               'framework'),
    ('Vue.js',              'framework'),
    ('Angular',             'framework'),
    ('Next.js',             'framework'),
    ('HTML',                'framework'),
    ('CSS',                 'framework'),
    ('Tailwind CSS',        'framework'),
    -- Databases
    ('PostgreSQL',          'database'),
    ('MySQL',               'database'),
    ('MongoDB',             'database'),
    ('Redis',               'database'),
    ('SQLite',              'database'),
    ('Elasticsearch',       'database'),
    -- Cloud
    ('AWS',                 'cloud'),
    ('Azure',               'cloud'),
    ('GCP',                 'cloud'),
    ('Heroku',              'cloud'),
    -- Tools
    ('Git',                 'tool'),
    ('GitHub',              'tool'),
    ('REST API',            'tool'),
    ('GraphQL',             'tool'),
    ('Postman',             'tool'),
    ('Linux',               'tool'),
    ('Jupyter',             'tool'),
    ('VS Code',             'tool'),
    -- Soft Skills
    ('Communication',       'soft_skill'),
    ('Problem Solving',     'soft_skill'),
    ('Teamwork',            'soft_skill'),
    ('Leadership',          'soft_skill'),
    ('Time Management',     'soft_skill')
ON CONFLICT (skill_name) DO NOTHING;


-- =============================================================================
-- VERIFY: shows all created tables and their disk size
-- =============================================================================
SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size('public.' || tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
