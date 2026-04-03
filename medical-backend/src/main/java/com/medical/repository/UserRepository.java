package com.medical.repository;

import com.medical.entity.User;
import org.apache.ibatis.annotations.*;
import java.util.Optional;

@Mapper
public interface UserRepository {
    @Select("SELECT * FROM sys_user WHERE username = #{username}")
    Optional<User> findByUsername(String username);

    @Select("SELECT * FROM sys_user WHERE id = #{id}")
    Optional<User> findById(Long id);

    @Select("SELECT * FROM sys_user")
    java.util.List<User> findAll();
}
