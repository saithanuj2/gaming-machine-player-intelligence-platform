USE GamingIntelligenceDB;
GO

/* Drop fact tables first because they depend on dimension tables */

IF OBJECT_ID('dbo.fact_gaming_transaction', 'U') IS NOT NULL
    DROP TABLE dbo.fact_gaming_transaction;
GO

IF OBJECT_ID('dbo.fact_machine_event', 'U') IS NOT NULL
    DROP TABLE dbo.fact_machine_event;
GO

IF OBJECT_ID('dbo.fact_player_session', 'U') IS NOT NULL
    DROP TABLE dbo.fact_player_session;
GO

IF OBJECT_ID('dbo.dim_machine', 'U') IS NOT NULL
    DROP TABLE dbo.dim_machine;
GO

IF OBJECT_ID('dbo.dim_player', 'U') IS NOT NULL
    DROP TABLE dbo.dim_player;
GO

IF OBJECT_ID('dbo.dim_location', 'U') IS NOT NULL
    DROP TABLE dbo.dim_location;
GO


/* =========================================================
   Dimension: Location
   ========================================================= */

CREATE TABLE dbo.dim_location
(
    location_id       VARCHAR(20)  NOT NULL,
    location_name     VARCHAR(150) NOT NULL,
    city              VARCHAR(100) NOT NULL,
    state             VARCHAR(10)  NOT NULL,
    region            VARCHAR(50)  NOT NULL,
    route_manager     VARCHAR(150) NOT NULL,
    location_type     VARCHAR(50)  NOT NULL,
    opening_date      DATE         NOT NULL,
    active_flag       BIT          NOT NULL,

    CONSTRAINT PK_dim_location
        PRIMARY KEY (location_id),

    CONSTRAINT CK_dim_location_active_flag
        CHECK (active_flag IN (0, 1))
);
GO


/* =========================================================
   Dimension: Player
   ========================================================= */

CREATE TABLE dbo.dim_player
(
    player_id          VARCHAR(20) NOT NULL,
    enrollment_date    DATE        NOT NULL,
    loyalty_tier       VARCHAR(30) NOT NULL,
    age_band           VARCHAR(20) NOT NULL,
    home_region        VARCHAR(50) NOT NULL,
    marketing_opt_in   BIT         NOT NULL,
    active_flag        BIT         NOT NULL,

    CONSTRAINT PK_dim_player
        PRIMARY KEY (player_id),

    CONSTRAINT CK_dim_player_marketing_opt_in
        CHECK (marketing_opt_in IN (0, 1)),

    CONSTRAINT CK_dim_player_active_flag
        CHECK (active_flag IN (0, 1))
);
GO


/* =========================================================
   Dimension: Machine
   ========================================================= */

CREATE TABLE dbo.dim_machine
(
    machine_id             VARCHAR(20)  NOT NULL,
    location_id            VARCHAR(20)  NOT NULL,
    manufacturer           VARCHAR(100) NOT NULL,
    cabinet_type           VARCHAR(50)  NOT NULL,
    game_title             VARCHAR(100) NOT NULL,
    game_category          VARCHAR(50)  NOT NULL,
    install_date           DATE         NOT NULL,
    software_version       VARCHAR(30)  NOT NULL,
    machine_status         VARCHAR(30)  NOT NULL,
    theoretical_hold_pct   DECIMAL(8,4) NOT NULL,

    CONSTRAINT PK_dim_machine
        PRIMARY KEY (machine_id),

    CONSTRAINT FK_dim_machine_location
        FOREIGN KEY (location_id)
        REFERENCES dbo.dim_location(location_id),

    CONSTRAINT CK_dim_machine_hold_pct
        CHECK (
            theoretical_hold_pct >= 0
            AND theoretical_hold_pct <= 1
        )
);
GO


/* =========================================================
   Fact: Player Session
   ========================================================= */

CREATE TABLE dbo.fact_player_session
(
    session_id                 BIGINT        NOT NULL,
    player_id                  VARCHAR(20)   NOT NULL,
    machine_id                 VARCHAR(20)   NOT NULL,
    location_id                VARCHAR(20)   NOT NULL,
    session_start              DATETIME2(6)  NOT NULL,
    session_end                DATETIME2(6)  NOT NULL,
    session_duration_minutes   INT           NOT NULL,
    total_rounds               INT           NOT NULL,
    total_wager                DECIMAL(18,2) NOT NULL,
    total_payout               DECIMAL(18,2) NOT NULL,
    net_gaming_revenue         DECIMAL(18,2) NOT NULL,

    CONSTRAINT PK_fact_player_session
        PRIMARY KEY (session_id),

    CONSTRAINT FK_session_player
        FOREIGN KEY (player_id)
        REFERENCES dbo.dim_player(player_id),

    CONSTRAINT FK_session_machine
        FOREIGN KEY (machine_id)
        REFERENCES dbo.dim_machine(machine_id),

    CONSTRAINT FK_session_location
        FOREIGN KEY (location_id)
        REFERENCES dbo.dim_location(location_id),

    CONSTRAINT CK_session_duration
        CHECK (session_duration_minutes > 0),

    CONSTRAINT CK_session_rounds
        CHECK (total_rounds > 0),

    CONSTRAINT CK_session_wager
        CHECK (total_wager >= 0),

    CONSTRAINT CK_session_payout
        CHECK (total_payout >= 0),

    CONSTRAINT CK_session_timestamp
        CHECK (session_end > session_start)
);
GO


/* =========================================================
   Fact: Gaming Transaction
   ========================================================= */

CREATE TABLE dbo.fact_gaming_transaction
(
    transaction_id          BIGINT        NOT NULL,
    session_id              BIGINT        NOT NULL,
    player_id               VARCHAR(20)   NOT NULL,
    machine_id              VARCHAR(20)   NOT NULL,
    location_id             VARCHAR(20)   NOT NULL,
    transaction_timestamp   DATETIME2(6)  NOT NULL,
    wager_amount            DECIMAL(18,2) NOT NULL,
    payout_amount           DECIMAL(18,2) NOT NULL,
    jackpot_amount          DECIMAL(18,2) NOT NULL,
    net_gaming_revenue      DECIMAL(18,2) NOT NULL,
    transaction_type        VARCHAR(30)   NOT NULL,

    CONSTRAINT PK_fact_gaming_transaction
        PRIMARY KEY (transaction_id),

    CONSTRAINT FK_transaction_session
        FOREIGN KEY (session_id)
        REFERENCES dbo.fact_player_session(session_id),

    CONSTRAINT FK_transaction_player
        FOREIGN KEY (player_id)
        REFERENCES dbo.dim_player(player_id),

    CONSTRAINT FK_transaction_machine
        FOREIGN KEY (machine_id)
        REFERENCES dbo.dim_machine(machine_id),

    CONSTRAINT FK_transaction_location
        FOREIGN KEY (location_id)
        REFERENCES dbo.dim_location(location_id),

    CONSTRAINT CK_transaction_wager
        CHECK (wager_amount >= 0),

    CONSTRAINT CK_transaction_payout
        CHECK (payout_amount >= 0),

    CONSTRAINT CK_transaction_jackpot
        CHECK (jackpot_amount >= 0)
);
GO


/* =========================================================
   Fact: Machine Event
   ========================================================= */

CREATE TABLE dbo.fact_machine_event
(
    event_id                   BIGINT       NOT NULL,
    machine_id                 VARCHAR(20)  NOT NULL,
    location_id                VARCHAR(20)  NOT NULL,
    event_timestamp            DATETIME2(6) NOT NULL,
    event_type                 VARCHAR(60)  NOT NULL,
    severity                   VARCHAR(20)  NOT NULL,
    downtime_minutes           INT          NOT NULL,
    software_version           VARCHAR(30)  NOT NULL,
    error_code                 VARCHAR(20)  NOT NULL,
    event_date                 DATE         NOT NULL,
    requires_investigation     BIT          NOT NULL,
    planned_event_flag         BIT          NOT NULL,

    CONSTRAINT PK_fact_machine_event
        PRIMARY KEY (event_id),

    CONSTRAINT FK_event_machine
        FOREIGN KEY (machine_id)
        REFERENCES dbo.dim_machine(machine_id),

    CONSTRAINT FK_event_location
        FOREIGN KEY (location_id)
        REFERENCES dbo.dim_location(location_id),

    CONSTRAINT CK_event_downtime
        CHECK (downtime_minutes >= 0),

    CONSTRAINT CK_event_investigation
        CHECK (requires_investigation IN (0, 1)),

    CONSTRAINT CK_event_planned
        CHECK (planned_event_flag IN (0, 1)),

    CONSTRAINT CK_event_severity
        CHECK (
            severity IN (
                'Low',
                'Medium',
                'High',
                'Critical'
            )
        )
);
GO


/* =========================================================
   Indexes
   ========================================================= */

CREATE INDEX IX_dim_machine_location
ON dbo.dim_machine(location_id);
GO

CREATE INDEX IX_session_player
ON dbo.fact_player_session(player_id);
GO

CREATE INDEX IX_session_machine
ON dbo.fact_player_session(machine_id);
GO

CREATE INDEX IX_session_location
ON dbo.fact_player_session(location_id);
GO

CREATE INDEX IX_session_start
ON dbo.fact_player_session(session_start);
GO

CREATE INDEX IX_transaction_session
ON dbo.fact_gaming_transaction(session_id);
GO

CREATE INDEX IX_transaction_player
ON dbo.fact_gaming_transaction(player_id);
GO

CREATE INDEX IX_transaction_machine
ON dbo.fact_gaming_transaction(machine_id);
GO

CREATE INDEX IX_transaction_location
ON dbo.fact_gaming_transaction(location_id);
GO

CREATE INDEX IX_transaction_timestamp
ON dbo.fact_gaming_transaction(transaction_timestamp);
GO

CREATE INDEX IX_event_machine
ON dbo.fact_machine_event(machine_id);
GO

CREATE INDEX IX_event_location
ON dbo.fact_machine_event(location_id);
GO

CREATE INDEX IX_event_timestamp
ON dbo.fact_machine_event(event_timestamp);
GO

CREATE INDEX IX_event_type_severity
ON dbo.fact_machine_event(event_type, severity);
GO


PRINT 'All GamingIntelligenceDB tables created successfully.';
GO