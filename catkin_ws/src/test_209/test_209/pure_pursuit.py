import rclpy, time
from rclpy.node import Node
from geometry_msgs.msg import Twist, Point, PoseStamped
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry, Path
from squaternion import Quaternion
from math import atan2, sqrt, pi
import numpy as np

class PurePursuit(Node):
    def __init__(self):
        super().__init__('pure_pursuit_path_tracking')
        self.cmd_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        # self.cmd_sub = self.create_subscription(Twist, 'cmd_vel', self.check_velocity, 10)
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.odom_callback, 10)
        self.path_sub = self.create_subscription(Path, '/local_path', self.path_callback, 10)
        self.goal_pub = self.create_publisher(PoseStamped,'goal_pose', 10)
        self.goal_sub = self.create_subscription(PoseStamped,'goal_pose',self.goal_callback,15)
        self.lidar_sub = self.create_subscription(LaserScan, '/scan', self.lidar_callback, 10)

        self.goal_msg = PoseStamped()
        self.goal_msg.header.frame_id = 'map'

        self.collision = False
        self.is_odom = False
        self.is_path = False
        self.odom_msg = Odometry()
        self.path_msg = Path()
        self.goal = [184, 224]

        self.lookahead_distance = 1.0  
        self.timer = self.create_timer(0.1, self.timer_callback)  

    def odom_callback(self, msg):
        self.is_odom = True
        self.odom_msg = msg

    def path_callback(self, msg):
        self.is_path = True
        self.path_msg = msg

    def goal_callback(self,msg):
        if msg.header.frame_id=='map':
            goal_x=msg.pose.position.x
            goal_y=msg.pose.position.y
        self.goal = [goal_x, goal_y]

    def check_collision(self, msg):
        for angle,r in enumerate(msg.ranges):
            if angle < 20 or angle > 340:
                if 0.0 < r < 0.2:
                    return True
        return False
    
    # def check_velocity(self, msg):
    #     # cmd_msg = Twist()
    #     self.speed = msg.linear.x
    #     if self.speed == 0:
    #     # 속도가 0이 된 첫 순간의 시간을 기록
    #         if not hasattr(self, 'zero_speed_start_time'):
    #             self.zero_speed_start_time = time.time()
    #         # 현재 시간과 속도가 0이 된 시간의 차이가 3초 이상이면 True 반환
    #         elif time.time() - self.zero_speed_start_time >= 3.0:
    #             return True
    #     else:
    #         # 속도가 0이 아니면, 시간 기록을 리셋
    #         self.zero_speed_start_time = None
    #     return False
    
    def lidar_callback(self, msg):
        self.lidar_msg = msg

        if self.is_path == True and self.is_odom == True:
            self.collision = self.check_collision(msg)
            self.is_lidar = True


    def timer_callback(self):
        if self.is_odom and self.is_path:
            path_points = [pose.pose.position for pose in self.path_msg.poses]
            robot_pose_x = self.odom_msg.pose.pose.position.x
            robot_pose_y = self.odom_msg.pose.pose.position.y

            closest_point, lookahead_point = self.find_lookahead_point(path_points, robot_pose_x, robot_pose_y)

            cmd_msg = Twist()  # cmd_msg를 여기서 초기화

            if lookahead_point is not None:
                
                if self.collision:
                    start_time = time.time()  # 현재 시간 기록
                    while True:
                        if time.time() - start_time < 1:  # 1초 동안 실행
                            cmd_msg.linear.x = -0.3
                            # print('후진중!!')
                        else:
                            cmd_msg.linear.x = 0.0
                            self.cmd_pub.publish(cmd_msg)

                            break
                        self.cmd_pub.publish(cmd_msg)

                    cmd_msg.linear.x = 0.0
                    self.cmd_pub.publish(cmd_msg)
           

                    goal_x = self.goal[0]
                    goal_y = self.goal[1]

                    self.goal_msg.pose.position.x = goal_x
                    self.goal_msg.pose.position.y = goal_y

                    self.goal_msg.pose.orientation.x = 0.0
                    self.goal_msg.pose.orientation.y = 0.0
                    self.goal_msg.pose.orientation.z = 0.0
                    self.goal_msg.pose.orientation.w = 1.0

                    # print(self.goal)
                    self.goal_msg.header.stamp = rclpy.clock.Clock().now().to_msg()
                    self.goal_pub.publish(self.goal_msg)

                else:
                    robot_orientation_q = self.odom_msg.pose.pose.orientation
                    robot_orientation_euler = Quaternion(robot_orientation_q.w, robot_orientation_q.x, robot_orientation_q.y, robot_orientation_q.z).to_euler()
                    robot_yaw = robot_orientation_euler[2]

                    angle_to_target = atan2(lookahead_point.y - robot_pose_y, lookahead_point.x - robot_pose_x)
                    theta = self.normalize_angle(angle_to_target - robot_yaw)

                    if theta > 1.5 or theta < -1.5:
                        cmd_msg.linear.x = 0.0
                        cmd_msg.angular.z = -theta/2

                    elif 0.7 < theta < 1.5 or -1.5 < theta < -0.7:
                        cmd_msg.linear.x = 0.2
                        cmd_msg.angular.z = -theta/3
                    
                    elif 0.2 < theta <= 0.7 or -0.7 <= theta < -0.2:
                        cmd_msg.linear.x = 0.5
                        cmd_msg.angular.z = -theta/4

                    else:
                        if 0.2 < self.lidar_msg.ranges[0]/5 < 1.0:
                            cmd_msg.linear.x = self.lidar_msg.ranges[0]/5
                        elif self.lidar_msg.ranges[0]/5 > 1.0:
                            cmd_msg.linear.x = 1.0
                        else:
                            cmd_msg.linear.x = 0.2
                        #self.cmd_msg.linear.x = min(1.0, self.lidar_msg.ranges[0]/5)
                        cmd_msg.angular.z = -theta/5


            else:
                cmd_msg.linear.x = 0.0
                cmd_msg.angular.z = 0.0

            self.cmd_pub.publish(cmd_msg)


    def find_lookahead_point(self, path_points, robot_position_x, robot_position_y):
        closest_distance = float('inf')
        lookahead_point = None
        for point in path_points:
            distance = sqrt((point.x - robot_position_x)**2 + (point.y - robot_position_y)**2)
            if self.lookahead_distance <= distance < closest_distance:
                closest_distance = distance
                lookahead_point = point

        # # 추가 로직: lookahead point가 결정되지   않았다면, 가장 가까운 포인트를 사용
        # if lookahead_point is None and path_points:
        #     min_dist_point = min(path_points, key=lambda point: sqrt((point.x - robot_position_x)**2 + (point.y - robot_position_y)**2))
        #     if sqrt((min_dist_point.x - robot_position_x)**2 + (min_dist_point.y - robot_position_y)**2) < self.lookahead_distance * 2:
        #         lookahead_point = min_dist_point

        return None, lookahead_point


    def normalize_angle(self, angle):
        while angle > pi:
            angle -= 2 * pi
        while angle < -pi:
            angle += 2 * pi
        return angle

def main(args=None):
    rclpy.init(args=args)
    pure_pursuit_node = PurePursuit()
    rclpy.spin(pure_pursuit_node)
    pure_pursuit_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
