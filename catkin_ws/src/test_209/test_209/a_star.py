import rclpy
import numpy as np
from rclpy.node import Node
import os
from geometry_msgs.msg import Pose,PoseStamped
from squaternion import Quaternion
from nav_msgs.msg import Odometry,OccupancyGrid,MapMetaData,Path
from math import pi,cos,sin
from collections import deque

# a_star 노드는  OccupancyGrid map을 받아 grid map 기반 최단경로 탐색 알고리즘을 통해 로봇이 목적지까지 가는 경로를 생성하는 노드입니다.
# 로봇의 위치(/pose), 맵(/map), 목표 위치(/goal_pose)를 받아서 전역경로(/global_path)를 만들어 줍니다. 
# goal_pose는 rviz2에서 2D Goal Pose 버튼을 누르고 위치를 찍으면 메시지가 publish 됩니다. 
# 주의할 점 : odom을 받아서 사용하는데 기존 odom 노드는 시작했을 때 로봇의 초기 위치가 x,y,heading(0,0,0) 입니다. 로봇의 초기위치를 맵 상에서 로봇의 위치와 맞춰줘야 합니다. 
# 따라서 sub2의 odom 노드를 수정해줍니다. turtlebot_status 안에는 정답데이터(절대 위치)가 있는데 그 정보를 사용해서 맵과 로봇의 좌표를 맞춰 줍니다.

# 노드 로직 순서
# 1. publisher, subscriber 만들기
# 2. 파라미터 설정
# 3. 맵 데이터 행렬로 바꾸기
# 4. 위치(x,y)를 map의 grid cell로 변환
# 5. map의 grid cell을 위치(x,y)로 변환
# 6. goal_pose 메시지 수신하여 목표 위치 설정
# 7. grid 기반 최단경로 탐색

class a_star(Node):

    def __init__(self):
        super().__init__('a_Star')
        # 로직 1. publisher, subscriber 만들기
        self.map_sub = self.create_subscription(OccupancyGrid,'map',self.map_callback,1)
        self.odom_sub = self.create_subscription(Odometry,'odom',self.odom_callback,1)
        self.goal_sub = self.create_subscription(PoseStamped,'goal_pose',self.goal_callback,1)
        self.a_star_pub= self.create_publisher(Path, 'global_path', 1)
        
        self.map_msg=OccupancyGrid()
        self.odom_msg=Odometry()
        self.is_map=False
        self.is_odom=False
        self.is_found_path=False
        self.is_grid_update=False


        # 로직 2. 파라미터 설정
        self.goal = [184,224] 
        self.map_size_x=350
        self.map_size_y=350
        self.map_resolution=0.05
        self.map_offset_x=-8-8.75
        self.map_offset_y=-4-8.75
    
        self.GRIDSIZE=350
 
        self.dx = [-1,0,0,1,-1,-1,1,1]
        self.dy = [0,1,-1,0,-1,1,-1,1]
        self.dCost = [1,1,1,1,1.414,1.414,1.414,1.414]
       

    def grid_update(self):
        self.is_grid_update=True
        
        # 로직 3. 맵 데이터 행렬로 바꾸기
        self.map_to_grid = np.array(self.map_msg.data).reshape((self.map_size_x, self.map_size_y)).transpose()
        # self.map_to_grid = np.array(self.map_msg.data).reshape((self.map_size_x, self.map_size_y))
        self.grid = np.where(self.map_to_grid > 30, 1, 0)  # Obstacle cells as 1, free space as 0

        file_path_1 = 'C:\\Users\\SSAFY\\Desktop\\S10P22A209\\catkin_ws\\src\\test_209\\map\\astar.txt'
        file_path_2 = 'C:\\Users\\SSAFY\\Desktop\\S10P22A209\\catkin_ws\\src\\test_209\\map\\astarmap.txt'

        # 맵 정보를 텍스트 형식으로 변환하여 저장
        with open(file_path_1, 'w') as f:
            for row in self.grid:
                # 한 행씩 파일에 쓰기
                f.write(' '.join(map(str, row)) + '\n')

        # 맵 정보를 텍스트 형식으로 변환하여 저장
        with open(file_path_2, 'w') as f:
            for row in self.map_to_grid:
                # 한 행씩 파일에 쓰기
                f.write(' '.join(map(str, row)) + '\n')


    def pose_to_grid_cell(self,x,y):

        # 로직 4. 위치(x,y)를 map의 grid cell로 변환 
        # (테스트) pose가 (-8,-4)라면 맵의 중앙에 위치하게 된다. 따라서 map_point_x,y 는 map size의 절반인 (175,175)가 된다.
        # pose가 (-16.75,12.75) 라면 맵의 시작점에 위치하게 된다. 따라서 map_point_x,y는 (0,0)이 된다.
        map_point_x = int((x - self.map_offset_x) / self.map_resolution)
        map_point_y = int((y - self.map_offset_y) / self.map_resolution)
        
        return map_point_x,map_point_y


    def grid_cell_to_pose(self,grid_cell):
        
        # 로직 5. map의 grid cell을 위치(x,y)로 변환
        # (테스트) grid cell이 (175,175)라면 맵의 중앙에 위치하게 된다. 따라서 pose로 변환하게 되면 맵의 중앙인 (-8,-4)가 된다.
        # grid cell이 (350,350)라면 맵의 제일 끝 좌측 상단에 위치하게 된다. 따라서 pose로 변환하게 되면 맵의 좌측 상단인 (0.75,6.25)가 된다.

        x = grid_cell[0] * self.map_resolution + self.map_offset_x
        y = grid_cell[1] * self.map_resolution + self.map_offset_y

        return [x,y]


    def odom_callback(self,msg):
        self.is_odom=True
        self.odom_msg=msg


    def map_callback(self,msg):
        self.is_map=True
        self.map_msg=msg
        

    def goal_callback(self,msg):
        
        if msg.header.frame_id=='map':
            # 로직 6. goal_pose 메시지 수신하여 목표 위치 설정
            goal_x=msg.pose.position.x
            goal_y=msg.pose.position.y
            goal_cell=self.pose_to_grid_cell(goal_x, goal_y)
            self.goal = goal_cell
            # print(msg)
            

            if self.is_map ==True and self.is_odom==True  :
                if self.is_grid_update==False :
                    self.grid_update()

        
                self.final_path=[]

                x=self.odom_msg.pose.pose.position.x
                y=self.odom_msg.pose.pose.position.y
                start_grid_cell=self.pose_to_grid_cell(x,y)

                self.path = [[0 for col in range(self.GRIDSIZE)] for row in range(self.GRIDSIZE)]
                self.cost = np.array([[self.GRIDSIZE*self.GRIDSIZE for col in range(self.GRIDSIZE)] for row in range(self.GRIDSIZE)], dtype=float)

                
                # 다익스트라 알고리즘을 완성하고 주석을 해제 시켜주세요. 
                # 시작지, 목적지가 탐색가능한 영역이고, 시작지와 목적지가 같지 않으면 경로탐색을 합니다.

                print(f'start : {start_grid_cell}, {self.map_to_grid[start_grid_cell[0]][start_grid_cell[1]]} ,goal : {self.goal},{self.map_to_grid[self.goal[0]][self.goal[1]]}')
                # print(f'start : {start_grid_cell}, {self.map_to_grid[start_grid_cell[1]][start_grid_cell[0]]} ,goal : {self.goal},{self.map_to_grid[self.goal[1]][self.goal[0]]}')
                # if self.grid[start_grid_cell[0]][ start_grid_cell[1]] ==0  and self.grid[self.goal[0]][self.goal[1]] ==0  and start_grid_cell != self.goal :
                # if self.grid[self.goal[1]][self.goal[0]] ==0  and start_grid_cell != self.goal :
                if self.grid[self.goal[0]][self.goal[1]] ==0  and start_grid_cell != self.goal :
                    self.dijkstra(start_grid_cell)
                else:
                    print('na')


                self.global_path_msg=Path()
                self.global_path_msg.header.frame_id='map'
                print(self.final_path)
                for grid_cell in reversed(self.final_path) :
                    tmp_pose=PoseStamped()
                    waypoint_x,waypoint_y=self.grid_cell_to_pose(grid_cell)
                    tmp_pose.pose.position.x=waypoint_x
                    tmp_pose.pose.position.y=waypoint_y
                    tmp_pose.pose.orientation.w=1.0
                    self.global_path_msg.poses.append(tmp_pose)
            
                if len(self.final_path)!=0 :
                    self.a_star_pub.publish(self.global_path_msg)

    def dijkstra(self,start):
        Q = deque()
        Q.append(start)
        self.cost[start[0]][start[1]] = 0
        found = False
        
        # 로직 7. grid 기반 최단경로 탐색
        
        while Q:
            current = Q.popleft()
            if current == self.goal:
                found = True
                break

            # for i in range(8):
            #     next = (current[0] + self.dx[i], current[1] + self.dy[i])
            #     if 0 <= next[0] < self.GRIDSIZE and 0 <= next[1] < self.GRIDSIZE:
            #         # if self.grid[next[1]][next[0]] == 0:  # If next is not an obstacle
            #         if self.grid[next[0]][next[1]] == 0:  # If next is not an obstacle
            #             new_cost = self.cost[current[0]][current[1]] + self.dCost[i]
            #             if self.cost[next[0]][next[1]] > new_cost:
            #                 Q.append(next)
            #                 self.path[next[0]][next[1]] = current
            #                 self.cost[next[0]][next[1]] = new_cost

            for i in range(8):
                next = (current[0] + self.dx[i], current[1] + self.dy[i])
                if 0 <= next[0] < self.GRIDSIZE and 0 <= next[1] < self.GRIDSIZE:
                    # Check if the 3x3 area around the next point is all zero
                    area_is_clear = True
                    for x in range(next[0]-2, next[0]+3):
                        for y in range(next[1]-2, next[1]+3):
                            if not (0 <= x < self.GRIDSIZE and 0 <= y < self.GRIDSIZE):
                                area_is_clear = False
                                break
                            if self.grid[x][y] != 0:
                                area_is_clear = False
                                break
                        if not area_is_clear:
                            break

                    if area_is_clear:
                        new_cost = self.cost[current[0]][current[1]] + self.dCost[i]
                        if self.cost[next[0]][next[1]] > new_cost:
                            Q.append(next)
                            self.path[next[0]][next[1]] = current
                            self.cost[next[0]][next[1]] = new_cost
        if found:
            node = self.goal
            while node != start:
                self.final_path.append(node)
                node = self.path[node[0]][node[1]]                

        
def main(args=None):
    rclpy.init(args=args)

    global_planner = a_star()

    rclpy.spin(global_planner)


    global_planner.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
