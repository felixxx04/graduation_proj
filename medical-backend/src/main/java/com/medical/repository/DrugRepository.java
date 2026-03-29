package com.medical.repository;

import com.medical.entity.Drug;
import org.apache.ibatis.annotations.*;
import java.util.List;

@Mapper
public interface DrugRepository {
    @Select("SELECT * FROM drug ORDER BY id")
    List<Drug> findAll();
    
    @Select("SELECT * FROM drug WHERE id = #{id}")
    Drug findById(Long id);
    
    @Select("SELECT * FROM drug WHERE category = #{category}")
    List<Drug> findByCategory(String category);
}
