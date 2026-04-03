USE medical_recommendation;
UPDATE sys_user SET password_hash = '$2a$10$lut2nnnjykVjZ.8lPGoyPuwr9q1LnGVK8tMLJ0tNc20L59nqk1QBm' WHERE username IN ('admin', 'doctor1', 'researcher1');
