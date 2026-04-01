-- Tenant DB template (RBAC removed, user_permissions enabled)
-- SAFE FOR Spring ScriptUtils

SET FOREIGN_KEY_CHECKS = 0;

-- =====================
-- users
-- =====================
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `user_id` BIGINT NOT NULL AUTO_INCREMENT,
  `email` VARCHAR(255) NOT NULL,
  `enabled` TINYINT(1) DEFAULT 1,
  `first_name` VARCHAR(255) DEFAULT NULL,
  `last_name` VARCHAR(255) DEFAULT NULL,
  `password` VARCHAR(255) DEFAULT NULL,
  `phone` VARCHAR(255) DEFAULT NULL,
  `role_name` VARCHAR(50) NOT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `uk_users_email` (`email`),
  UNIQUE KEY `uk_users_phone` (`phone`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- user_permissions
-- =====================
DROP TABLE IF EXISTS `user_permissions`;
CREATE TABLE `user_permissions` (
  `user_permission_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `permission_name` VARCHAR(150) NOT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_permission_id`),
  UNIQUE KEY `uk_user_permission` (`user_id`, `permission_name`),
  CONSTRAINT `fk_user_permissions_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- address
-- =====================
DROP TABLE IF EXISTS `address`;
CREATE TABLE `address` (
  `address_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `pin_code` BIGINT DEFAULT NULL,
  `district` VARCHAR(255) DEFAULT NULL,
  `mandal` VARCHAR(255) DEFAULT NULL,
  `city` VARCHAR(255) DEFAULT NULL,
  `village` VARCHAR(255) DEFAULT NULL,
  `d_no` BIGINT DEFAULT NULL,
  PRIMARY KEY (`address_id`),
  UNIQUE KEY `uk_address_user` (`user_id`),
  CONSTRAINT `fk_address_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- admin
-- =====================
DROP TABLE IF EXISTS `admin`;
CREATE TABLE `admin` (
  `admin_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  PRIMARY KEY (`admin_id`),
  UNIQUE KEY `uk_admin_user` (`user_id`),
  CONSTRAINT `fk_admin_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- parents
-- =====================
DROP TABLE IF EXISTS `parents`;
CREATE TABLE `parents` (
  `parent_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  PRIMARY KEY (`parent_id`),
  UNIQUE KEY `uk_parent_user` (`user_id`),
  CONSTRAINT `fk_parent_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- students
-- =====================
DROP TABLE IF EXISTS `students`;
CREATE TABLE `students` (
  `student_id` BIGINT NOT NULL AUTO_INCREMENT,
  `dob` DATE DEFAULT NULL,
  `gender` VARCHAR(255) DEFAULT NULL,
  `user_id` BIGINT NOT NULL,
  PRIMARY KEY (`student_id`),
  UNIQUE KEY `uk_student_user` (`user_id`),
  CONSTRAINT `fk_student_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- parent_student_relation
-- =====================
DROP TABLE IF EXISTS `parent_student_relation`;
CREATE TABLE `parent_student_relation` (
  `rel_id` BIGINT NOT NULL AUTO_INCREMENT,
  `parent_id` BIGINT NOT NULL,
  `student_id` BIGINT NOT NULL,
  PRIMARY KEY (`rel_id`),
  CONSTRAINT `fk_ps_parent`
    FOREIGN KEY (`parent_id`)
    REFERENCES `parents` (`parent_id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_ps_student`
    FOREIGN KEY (`student_id`)
    REFERENCES `students` (`student_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- instructor
-- =====================
DROP TABLE IF EXISTS `instructor`;
CREATE TABLE `instructor` (
  `instructor_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  PRIMARY KEY (`instructor_id`),
  UNIQUE KEY `uk_instructor_user` (`user_id`),
  CONSTRAINT `fk_instructor_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- driver
-- =====================
DROP TABLE IF EXISTS `driver`;
CREATE TABLE `driver` (
  `driver_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  PRIMARY KEY (`driver_id`),
  UNIQUE KEY `uk_driver_user` (`user_id`),
  CONSTRAINT `fk_driver_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- conductor
-- =====================
DROP TABLE IF EXISTS `conductor`;
CREATE TABLE `conductor` (
  `conductor_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  PRIMARY KEY (`conductor_id`),
  UNIQUE KEY `uk_conductor_user` (`user_id`),
  CONSTRAINT `fk_conductor_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- accountant
-- =====================
DROP TABLE IF EXISTS `accountant`;
CREATE TABLE `accountant` (
  `accountant_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  PRIMARY KEY (`accountant_id`),
  UNIQUE KEY `uk_accountant_user` (`user_id`),
  CONSTRAINT `fk_accountant_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- affiliate
-- =====================
DROP TABLE IF EXISTS `affiliate`;
CREATE TABLE `affiliate` (
  `affiliate_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  PRIMARY KEY (`affiliate_id`),
  UNIQUE KEY `uk_affiliate_user` (`user_id`),
  CONSTRAINT `fk_affiliate_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- community_manager
-- =====================
DROP TABLE IF EXISTS `community_manager`;
CREATE TABLE `community_manager` (
  `community_manager_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  PRIMARY KEY (`community_manager_id`),
  UNIQUE KEY `uk_community_manager_user` (`user_id`),
  CONSTRAINT `fk_community_manager_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- department_head
-- =====================
DROP TABLE IF EXISTS `department_head`;
CREATE TABLE `department_head` (
  `department_head_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  PRIMARY KEY (`department_head_id`),
  UNIQUE KEY `uk_department_head_user` (`user_id`),
  CONSTRAINT `fk_department_head_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- evaluator
-- =====================
DROP TABLE IF EXISTS `evaluator`;
CREATE TABLE `evaluator` (
  `evaluator_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  PRIMARY KEY (`evaluator_id`),
  UNIQUE KEY `uk_evaluator_user` (`user_id`),
  CONSTRAINT `fk_evaluator_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- inventory_manager
-- =====================
DROP TABLE IF EXISTS `inventory_manager`;
CREATE TABLE `inventory_manager` (
  `inventory_manager_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  PRIMARY KEY (`inventory_manager_id`),
  UNIQUE KEY `uk_inventory_manager_user` (`user_id`),
  CONSTRAINT `fk_inventory_manager_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- librarian
-- =====================
DROP TABLE IF EXISTS `librarian`;
CREATE TABLE `librarian` (
  `librarian_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  PRIMARY KEY (`librarian_id`),
  UNIQUE KEY `uk_librarian_user` (`user_id`),
  CONSTRAINT `fk_librarian_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- marketing_manager
-- =====================
DROP TABLE IF EXISTS `marketing_manager`;
CREATE TABLE `marketing_manager` (
  `marketing_manager_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  PRIMARY KEY (`marketing_manager_id`),
  UNIQUE KEY `uk_marketing_manager_user` (`user_id`),
  CONSTRAINT `fk_marketing_manager_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- mentor
-- =====================
DROP TABLE IF EXISTS `mentor`;
CREATE TABLE `mentor` (
  `mentor_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  PRIMARY KEY (`mentor_id`),
  UNIQUE KEY `uk_mentor_user` (`user_id`),
  CONSTRAINT `fk_mentor_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- transport_manager
-- =====================
DROP TABLE IF EXISTS `transport_manager`;
CREATE TABLE `transport_manager` (
  `transport_manager_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  PRIMARY KEY (`transport_manager_id`),
  UNIQUE KEY `uk_transport_manager_user` (`user_id`),
  CONSTRAINT `fk_transport_manager_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- warden
-- =====================
DROP TABLE IF EXISTS `warden`;
CREATE TABLE `warden` (
  `warden_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  PRIMARY KEY (`warden_id`),
  UNIQUE KEY `uk_warden_user` (`user_id`),
  CONSTRAINT `fk_warden_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- audit_logs
-- =====================
DROP TABLE IF EXISTS `audit_logs`;
CREATE TABLE `audit_logs` (
  `audit_id` BIGINT NOT NULL AUTO_INCREMENT,
  `action` VARCHAR(255) DEFAULT NULL,
  `entity_name` VARCHAR(255) DEFAULT NULL,
  `entity_id` BIGINT DEFAULT NULL,
  `user_id` BIGINT DEFAULT NULL,
  `ip_address` VARCHAR(255) DEFAULT NULL,
  `created_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`audit_id`),
  CONSTRAINT `fk_audit_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- login_history
-- =====================
DROP TABLE IF EXISTS `login_history`;
CREATE TABLE `login_history` (
  `login_id` BIGINT NOT NULL AUTO_INCREMENT,
  `device` VARCHAR(255) DEFAULT NULL,
  `ip_address` VARCHAR(255) DEFAULT NULL,
  `login_time` DATETIME DEFAULT NULL,
  `user_agent` VARCHAR(255) DEFAULT NULL,
  `user_id` BIGINT NOT NULL,
  PRIMARY KEY (`login_id`),
  CONSTRAINT `fk_login_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- system_settings
-- =====================
DROP TABLE IF EXISTS `system_settings`;
CREATE TABLE `system_settings` (
  `setting_key` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `max_login_attempts` BIGINT NOT NULL,
  `acc_lock_duration` BIGINT NOT NULL,
  `pass_expiry_days` BIGINT NOT NULL,
  `pass_length` BIGINT NOT NULL,
  `jwt_expiry_mins` BIGINT DEFAULT NULL,
  `session_timeout` BIGINT DEFAULT NULL,
  `multi_session` TINYINT(1) DEFAULT 0,
  `enable_login_audit` TINYINT(1) DEFAULT 1,
  `enable_audit_log` TINYINT(1) DEFAULT 1,
  `password_last_updated_at` TIMESTAMP NULL DEFAULT NULL,
  `updated_time` DATETIME DEFAULT NULL,
  PRIMARY KEY (`setting_key`),
  UNIQUE KEY `uk_system_user` (`user_id`),
  CONSTRAINT `fk_system_settings_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- password_reset_tokens
-- =====================
DROP TABLE IF EXISTS `password_reset_tokens`;
CREATE TABLE `password_reset_tokens` (
  `token_id` BIGINT NOT NULL AUTO_INCREMENT,
  `reset_token` VARCHAR(255) NOT NULL,
  `user_id` BIGINT NOT NULL,
  `created_time` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`token_id`),
  CONSTRAINT `fk_reset_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- failed_login_attempts
-- =====================
DROP TABLE IF EXISTS `failed_login_attempts`;
CREATE TABLE `failed_login_attempts` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `attempt_time` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `ip_address` VARCHAR(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_failed_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- user_sessions
-- =====================
DROP TABLE IF EXISTS `user_sessions`;
CREATE TABLE `user_sessions` (
  `session_id` BIGINT NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT NOT NULL,
  `token` LONGTEXT,
  `login_time` TIMESTAMP NULL,
  `logout_time` TIMESTAMP NULL,
  `last_activity_time` DATETIME DEFAULT NULL,
  PRIMARY KEY (`session_id`),
  CONSTRAINT `fk_session_user`
    FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =====================
-- otp_verification
-- =====================
DROP TABLE IF EXISTS `otp_verification`;
CREATE TABLE `otp_verification` (
  `otp_id` BIGINT NOT NULL AUTO_INCREMENT,
  `email` VARCHAR(255) DEFAULT NULL,
  `phone` VARCHAR(20) DEFAULT NULL,
  `otp` VARCHAR(10) NOT NULL,
  `purpose` VARCHAR(50) NOT NULL,
  `expires_at` DATETIME NOT NULL,
  `attempts` INT DEFAULT 0,
  `max_attempts` INT DEFAULT 3,
  `verified` TINYINT(1) DEFAULT 0,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`otp_id`),
  UNIQUE KEY `uq_active_otp` (`email`, `purpose`, `verified`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS `tenant_themes`;
CREATE TABLE `tenant_themes` (
 `tenant_theme_id` BIGINT NOT NULL AUTO_INCREMENT,
 `theme_template_id` BIGINT NOT NULL,
 `status` VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
 `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 `header_config` JSON NULL,
 `default_header_config` JSON NULL,
 `footer_config` JSON NULL,
 `seo_config` JSON NULL,
 `robots_txt` TEXT,
 `sitemap_path` VARCHAR(500),
 PRIMARY KEY (`tenant_theme_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DROP TABLE IF EXISTS `tenant_pages`;
CREATE TABLE tenant_pages (
  tenant_page_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  tenant_theme_id BIGINT NOT NULL,
  page_key VARCHAR(50) NOT NULL,
  slug VARCHAR(150) NOT NULL,
  custom_title VARCHAR(255),
  is_published BOOLEAN DEFAULT 0,
  last_modified_at TIMESTAMP NULL,
  FOREIGN KEY (tenant_theme_id) REFERENCES tenant_themes(tenant_theme_id) ON DELETE CASCADE
);

DROP TABLE IF EXISTS `tenant_sections`;
CREATE TABLE tenant_sections (
    tenant_section_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tenant_page_id BIGINT NOT NULL,
    template_section_id BIGINT NOT NULL,
    section_type VARCHAR(50) NOT NULL,
    section_config JSON,
    display_order INT,
    FOREIGN KEY (tenant_page_id)
        REFERENCES tenant_pages(tenant_page_id)
        ON DELETE CASCADE
);

DROP TABLE IF EXISTS `tenant_settings`;
CREATE TABLE tenant_settings (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    site_name VARCHAR(255),
    logo_path VARCHAR(500),
    favicon_path VARCHAR(500),
    footfall_enabled BOOLEAN DEFAULT FALSE,
    store_view_type VARCHAR(50),
    store_config JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE tenant_headers (
    tenant_header_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    header_config JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tenant_custom_pages (
    tenant_custom_page_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL UNIQUE,
    meta_title VARCHAR(255),
    meta_description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE tenant_custom_page_sections (
    tenant_custom_page_section_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    tenant_custom_page_id BIGINT NOT NULL,
    section_type VARCHAR(100) NOT NULL,
    section_config JSON,
    display_order INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_custom_page
        FOREIGN KEY (tenant_custom_page_id)
        REFERENCES tenant_custom_pages(tenant_custom_page_id)
        ON DELETE CASCADE
);

CREATE TABLE community_spaces (
space_id BIGINT AUTO_INCREMENT PRIMARY KEY,
space_name VARCHAR(255) NOT NULL,
course_id BIGINT,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP NULL
);

CREATE TABLE community_channels (
channel_id BIGINT AUTO_INCREMENT PRIMARY KEY,
space_id BIGINT NOT NULL,
channel_name VARCHAR(255) NOT NULL,
channel_type VARCHAR(50),
description TEXT,
admins_only BOOLEAN DEFAULT FALSE,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE community_threads (
thread_id BIGINT AUTO_INCREMENT PRIMARY KEY,
channel_id BIGINT NOT NULL,
title VARCHAR(255),
content TEXT,
author_id BIGINT,
author_name VARCHAR(255),
author_role VARCHAR(50),
status VARCHAR(20) DEFAULT 'OPEN',
is_pinned BOOLEAN DEFAULT FALSE,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE community_replies (
reply_id BIGINT AUTO_INCREMENT PRIMARY KEY,
thread_id BIGINT,
parent_reply_id BIGINT,
content TEXT,
author_id BIGINT,
author_name VARCHAR(255),
author_role VARCHAR(50),
is_verified BOOLEAN DEFAULT FALSE,
is_answer BOOLEAN DEFAULT FALSE,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE community_reactions (
reaction_id BIGINT AUTO_INCREMENT PRIMARY KEY,
thread_id BIGINT,
reply_id BIGINT,
user_id BIGINT,
reaction_type VARCHAR(50),
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE community_bookmarks (
bookmark_id BIGINT AUTO_INCREMENT PRIMARY KEY,
thread_id BIGINT,
user_id BIGINT,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE community_mentions (
mention_id BIGINT AUTO_INCREMENT PRIMARY KEY,
thread_id BIGINT,
reply_id BIGINT,
mentioned_user_id BIGINT,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE community_notifications (
notification_id BIGINT AUTO_INCREMENT PRIMARY KEY,
user_id BIGINT,
thread_id BIGINT,
reply_id BIGINT,
type VARCHAR(50),
is_read BOOLEAN DEFAULT FALSE,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE community_reports (
report_id BIGINT AUTO_INCREMENT PRIMARY KEY,
thread_id BIGINT,
reply_id BIGINT,
reported_by BIGINT,
reason TEXT,
status VARCHAR(20) DEFAULT 'OPEN',
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE community_channel_members (
    member_id BIGINT NOT NULL AUTO_INCREMENT,
    channel_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    joined_at DATETIME DEFAULT NULL,
    PRIMARY KEY (member_id),
    UNIQUE KEY unique_member (channel_id, user_id),
    KEY idx_channel_id (channel_id),
    KEY idx_user_id (user_id)
);

SET FOREIGN_KEY_CHECKS = 1;
