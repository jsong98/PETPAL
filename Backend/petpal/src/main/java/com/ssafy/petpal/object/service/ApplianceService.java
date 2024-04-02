package com.ssafy.petpal.object.service;

import com.ssafy.petpal.home.entity.Home;
import com.ssafy.petpal.home.repository.HomeRepository;
import com.ssafy.petpal.object.dto.ApplianceRegisterDTO;
import com.ssafy.petpal.object.dto.ApplianceResponseDto;
import com.ssafy.petpal.object.entity.Appliance;
import com.ssafy.petpal.object.repository.ApplianceRepository;
import com.ssafy.petpal.room.entity.Room;
import com.ssafy.petpal.room.repository.RoomRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.locationtech.jts.geom.Point;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.Objects;

import static com.ssafy.petpal.object.dto.TargetRegisterDto.locationToPoint;

@Service
@Slf4j
@RequiredArgsConstructor
public class ApplianceService {

    private final ApplianceRepository applianceRepository;
    private final HomeRepository homeRepository;
    private final RoomRepository roomRepository;
    private final StringRedisTemplate redisTemplate;
    public void createAppliance(ApplianceRegisterDTO applianceRegisterDTO){
        Home home = homeRepository.findById(applianceRegisterDTO.getHomeId())
                .orElseThrow(IllegalArgumentException::new);
        Room room = roomRepository.findById(applianceRegisterDTO.getRoomId())
                .orElseThrow(IllegalArgumentException::new);

//         ROS2로 메세지 발행
//        http로 ROs야 맵데이터 다오
//              response = request(ros주소);
//         ROS2가 준 메세지 받기
//
        // mapRepository.save(map)
        Point point = locationToPoint(applianceRegisterDTO.getCoordinate());
        Appliance appliance = Appliance.builder()
                .applianceUUID(applianceRegisterDTO.getApplianceUUID())
                .applianceType(applianceRegisterDTO.getApplianceType())
                .coordinate(point)
                .home(home)
                .room(room)
                .build();
        Appliance appliance1  =applianceRepository.save(appliance);
        redisTemplate.opsForValue().set("home:" + applianceRegisterDTO.getHomeId() + ":appliance:" + appliance1.getId(), "OFF");
    }

    public ApplianceResponseDto fetchApplianceByUUID(String uuid){
        ApplianceResponseDto appliance = applianceRepository.findByApplianceUUID(uuid);
        appliance.setApplianceStatus(
                getApplianceStatus(appliance.getHomeId(), appliance.getApplianceId())
        );
        return appliance;
    }

    public List<ApplianceResponseDto> fetchAllApplianceByRoomId(Long roomId){
        List<ApplianceResponseDto> list = applianceRepository.findAllByRoomId(roomId);
        list.forEach(appliance -> {
            String applianceStatus = getApplianceStatus(appliance.getHomeId(), appliance.getApplianceId());
            if(applianceStatus==null){
                redisTemplate.opsForValue().set("home:"+appliance.getHomeId()+":appliance:"+appliance.getApplianceId(),"OFF");
                applianceStatus="OFF";
            }

            appliance.setApplianceStatus(
                applianceStatus
            );
        });
        return list;

    }

    public List<ApplianceResponseDto> fetchAllApplianceByHomeId(Long homeId){
        List<ApplianceResponseDto> list = applianceRepository.findAllByHomeId(homeId);
        list.forEach(appliance -> {
            appliance.setApplianceStatus(
                    getApplianceStatus(appliance.getHomeId(), appliance.getApplianceId())
            );
        });
        return list;
    }

    public void updateApplianceStatus(Long homeId, Long applianceId, String status) {

        redisTemplate.opsForValue().set("home:" + homeId + ":appliance:" + applianceId, status);

    }

    public String getApplianceStatus(Long homeId, Long applianceId) {
        String key = "home:" + homeId + ":appliance:" + applianceId;
        String value = redisTemplate.opsForValue().get(key);
        if (value != null) {
            try {
                return value;
            } catch (Exception e) {
                log.error("Invalid appliance status format for appliance " + applianceId, e);
                return "NULL"; // 상태를 알 수 없는 경우, 예: 잘못된 형식
            }
        } else {
            log.info("No status found for appliance " + applianceId + ", defaulting to NULL");
            return "NULL"; // Redis에서 조회된 값이 null인 경우
        }
    }

    public void deleteAppliance(Long applianceId) {
        Appliance appliance = applianceRepository.findById(applianceId)
                .orElseThrow(IllegalArgumentException::new);
        applianceRepository.delete(appliance);
    }

}
