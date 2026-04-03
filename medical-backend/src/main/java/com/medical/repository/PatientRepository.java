package com.medical.repository;

import com.medical.dto.response.PatientProfile;
import com.medical.entity.Patient;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface PatientRepository {

    @Select("SELECT * FROM patient ORDER BY id DESC")
    List<Patient> findAll();

    @Select("SELECT * FROM patient WHERE id = #{id}")
    Patient findById(Long id);

    @Insert("INSERT INTO patient(name, gender, birth_date, phone) VALUES(#{name}, #{gender}, #{birthDate}, #{phone})")
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(Patient patient);

    @Update("UPDATE patient SET name=#{name}, gender=#{gender}, birth_date=#{birthDate}, phone=#{phone} WHERE id=#{id}")
    int update(Patient patient);

    @Delete("DELETE FROM patient WHERE id = #{id}")
    int deleteById(Long id);

    // ========== 关联查询方法 ==========

    @Select("""
        SELECT
            p.id, p.name, p.gender, p.birth_date AS birthDate, p.phone, p.created_at AS createdAt,
            hr.age, hr.height, hr.weight, hr.blood_type AS bloodType,
            hr.chronic_diseases AS chronicDiseasesJson,
            hr.allergies AS allergiesJson,
            hr.current_medications AS currentMedicationsJson,
            hr.medical_history AS medicalHistory, hr.symptoms
        FROM patient p
        LEFT JOIN patient_health_record hr ON p.id = hr.patient_id AND (hr.is_latest = TRUE OR hr.is_latest IS NULL)
        ORDER BY p.id DESC
        """)
    @Results({
        @Result(property = "id", column = "id"),
        @Result(property = "name", column = "name"),
        @Result(property = "gender", column = "gender"),
        @Result(property = "birthDate", column = "birthDate"),
        @Result(property = "phone", column = "phone"),
        @Result(property = "age", column = "age"),
        @Result(property = "height", column = "height"),
        @Result(property = "weight", column = "weight"),
        @Result(property = "bloodType", column = "bloodType"),
        @Result(property = "medicalHistory", column = "medicalHistory"),
        @Result(property = "symptoms", column = "symptoms"),
        @Result(property = "createdAt", column = "createdAt"),
        @Result(property = "chronicDiseases", column = "chronicDiseasesJson", typeHandler = com.medical.repository.handler.JsonStringListHandler.class),
        @Result(property = "allergies", column = "allergiesJson", typeHandler = com.medical.repository.handler.JsonStringListHandler.class),
        @Result(property = "currentMedications", column = "currentMedicationsJson", typeHandler = com.medical.repository.handler.JsonStringListHandler.class),
    })
    List<PatientProfile> findAllProfiles();

    @Select("""
        SELECT
            p.id, p.name, p.gender, p.birth_date AS birthDate, p.phone, p.created_at AS createdAt,
            hr.age, hr.height, hr.weight, hr.blood_type AS bloodType,
            hr.chronic_diseases AS chronicDiseasesJson,
            hr.allergies AS allergiesJson,
            hr.current_medications AS currentMedicationsJson,
            hr.medical_history AS medicalHistory, hr.symptoms
        FROM patient p
        LEFT JOIN patient_health_record hr ON p.id = hr.patient_id AND (hr.is_latest = TRUE OR hr.is_latest IS NULL)
        WHERE p.id = #{id}
        """)
    @Results({
        @Result(property = "id", column = "id"),
        @Result(property = "name", column = "name"),
        @Result(property = "gender", column = "gender"),
        @Result(property = "birthDate", column = "birthDate"),
        @Result(property = "phone", column = "phone"),
        @Result(property = "age", column = "age"),
        @Result(property = "height", column = "height"),
        @Result(property = "weight", column = "weight"),
        @Result(property = "bloodType", column = "bloodType"),
        @Result(property = "medicalHistory", column = "medicalHistory"),
        @Result(property = "symptoms", column = "symptoms"),
        @Result(property = "createdAt", column = "createdAt"),
        @Result(property = "chronicDiseases", column = "chronicDiseasesJson", typeHandler = com.medical.repository.handler.JsonStringListHandler.class),
        @Result(property = "allergies", column = "allergiesJson", typeHandler = com.medical.repository.handler.JsonStringListHandler.class),
        @Result(property = "currentMedications", column = "currentMedicationsJson", typeHandler = com.medical.repository.handler.JsonStringListHandler.class),
    })
    PatientProfile findProfileById(Long id);
}
