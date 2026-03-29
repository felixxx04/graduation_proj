package com.medical.repository;

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
}
