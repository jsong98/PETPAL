package com.ssafy.petpal.control.controller;

import com.amazonaws.HttpMethod;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ssafy.petpal.control.dto.ControlDto;
import com.ssafy.petpal.control.dto.MessageContainer;
import com.ssafy.petpal.home.service.HomeService;
import com.ssafy.petpal.image.service.ImageService;
import com.ssafy.petpal.map.dto.MapDto;
import com.ssafy.petpal.map.service.MapService;
import com.ssafy.petpal.notification.dto.NotificationRequestDto;
import com.ssafy.petpal.notification.service.FcmService;
import com.ssafy.petpal.notification.service.NotificationService;
import com.ssafy.petpal.object.service.ApplianceService;
import com.ssafy.petpal.object.service.TargetService;
import com.ssafy.petpal.route.dto.RouteDto;
import com.ssafy.petpal.route.service.RouteService;
import com.ssafy.petpal.user.service.UserService;
import lombok.AllArgsConstructor;
import lombok.RequiredArgsConstructor;
import org.checkerframework.checker.units.qual.A;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.messaging.handler.annotation.DestinationVariable;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Controller;

import java.io.IOException;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;

@Controller
//@RequiredArgsConstructor
@AllArgsConstructor
public class ControlController {
    private final RabbitTemplate rabbitTemplate;
    private final ObjectMapper objectMapper;
    private final StringRedisTemplate redisTemplate;
    private final ApplianceService applianceService;
    private final MapService mapService;
    private final RouteService routeService;
    private final FcmService fcmService;
    private final HomeService homeService;
//    private final UserService userService;
    private final NotificationService notificationService;
    private final ImageService imageService;
    private final TargetService targetService;
    private static final String CONTROL_QUEUE_NAME = "control.queue";
    private static final String CONTROL_EXCHANGE_NAME = "control.exchange";



    @MessageMapping("control.message.{homeId}")
    public void sendMessage(@Payload String rawMessage, @DestinationVariable Long homeId) throws IOException {
//        logger.info("Received message: {}", rawMessage);
        ControlDto controlDto = objectMapper.readValue(rawMessage, ControlDto.class);
        String type = controlDto.getType();
        switch (type){
            //COMPLETE한게 가전 On/Off를 완료한 것인지 위험물 처리 프로세스를 완료한 것인지 구분을 할 필요가 있음.
            case "A_COMPLETE":
                // ROS에서 입증한 실제 가전상태 데이터를 redis에 올린다.
//                controlDto.getMessage() //parsing
                MessageContainer.A_Complete aComplete = objectMapper.readValue(controlDto.getMessage(),MessageContainer.A_Complete.class);
                if(aComplete.getIsSuccess()){
                    applianceService.updateApplianceStatus(homeId,aComplete.getApplianceId(),aComplete.getCurrentStatus());
                }else{
                    // 다시 발행
                }
//              fcm 호출.
                //가전 상태 제어 완료 알림 보내기!
                Long targetUserId = homeService.findKakaoIdByHomeId(homeId);
                LocalDateTime nowInKorea = LocalDateTime.now(ZoneId.of("Asia/Seoul"));

                DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");
                String formattedTime = nowInKorea.format(formatter);

                String downloadURL1 = imageService.generateURL(aComplete.getApplianceName()+".png", HttpMethod.GET);
                NotificationRequestDto notificationRequestDto1
                        = new NotificationRequestDto(targetUserId, type, aComplete.getApplianceName()+"의 상태를 변경하였습니다.",
                        formattedTime,downloadURL1);
                fcmService.sendMessageTo(notificationRequestDto1);
                notificationService.saveNotification(notificationRequestDto1); // DB에 저장
                break;
            case "ON": case "OFF":
            case "WEATHER": case "TURTLE":
            case "SCAN": case "IOT": case "MODE":
            case "REGISTER_REQUEST" : case "REGISTER_RESPONSE":
                rabbitTemplate.convertAndSend(CONTROL_EXCHANGE_NAME, "home." + homeId, controlDto);
                break;
            case "O_COMPLETE":
                MessageContainer.O_Complete oComplete =  objectMapper.readValue(controlDto.getMessage(), MessageContainer.O_Complete.class);
                String filename = targetService.fetchFilenameByTargetId(oComplete.getObjectId());
                String downloadURL = imageService.generateURL(filename, HttpMethod.GET);

                Long targetUserId2 = homeService.findKakaoIdByHomeId(homeId);
                LocalDateTime nowInKorea2 = LocalDateTime.now(ZoneId.of("Asia/Seoul"));

                DateTimeFormatter formatter2 = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");
                String formattedTime2 = nowInKorea2.format(formatter2);
                NotificationRequestDto notificationRequestDto2
                        = new NotificationRequestDto(targetUserId2, type, oComplete.getObjectType()+"를 처리하였습니다.",
                        formattedTime2,downloadURL);
                break;
            default:
                break;
        }
    }

    @MessageMapping("images.stream.{homeId}.images")
    public void sendImagesData(@Payload String rawMessage, @DestinationVariable String homeId) throws JsonProcessingException {
        ControlDto controlDto = objectMapper.readValue(rawMessage, ControlDto.class);
        //type : IMAGE
        rabbitTemplate.convertAndSend(CONTROL_EXCHANGE_NAME, "home." + homeId + ".images", controlDto);
    }

    @MessageMapping("images.stream.{homeId}.yolo")
    public void sendImagesDataYolo(@Payload String rawMessage, @DestinationVariable String homeId) throws JsonProcessingException {
        ControlDto controlDto = objectMapper.readValue(rawMessage, ControlDto.class);
        //type : YOLO
        rabbitTemplate.convertAndSend(CONTROL_EXCHANGE_NAME, "home." + homeId + ".yolo", controlDto);
    }

    @MessageMapping("scan.map.{homeId}")
    public void sendMapData(@Payload String rawMessage, @DestinationVariable String homeId) throws JsonProcessingException {
        ControlDto controlDto = objectMapper.readValue(rawMessage, ControlDto.class);
        String type = controlDto.getType();
        switch (type){
//            case "SCAN":
//                rabbitTemplate.convertAndSend(CONTROL_EXCHANGE_NAME, "home." + homeId, controlDto);
//                break;
            case "COMPLETE":
                // 날것의 맵
                // dtoMapper로 만들어서
                // mapService.createMap(dto)
                // 메세지 발행(깎은 맵이 들어가있다)
                MapDto mapDto = mapService.createMap(homeId, controlDto.getMessage());
                rabbitTemplate.convertAndSend(CONTROL_EXCHANGE_NAME, "home." + homeId, mapDto);
                break;
            case "ROUTE":
                // 경로 저장 repository
                RouteDto routeDto = routeService.saveRoute(homeId, controlDto.getMessage());
                break;
        }
    }

    @RabbitListener(queues = CONTROL_QUEUE_NAME)
    public void receive(ControlDto controlDto) {
//        logger.info(" log : " + controlDto);
    }


}
