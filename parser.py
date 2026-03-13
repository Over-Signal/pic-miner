from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import random
import requests
import os
import json

class parser:
    def __init__(self):
        self.driver = webdriver.Chrome()

    def human_scroll_naver(self, portal:str):
        img_counter = 0
        last_height = self.driver.execute_script("return document.body.scrollHeight")
    
    # 멈춘 횟수를 카운트하는 변수
        retries = 0 
        max_retries = 3  # 최대 3번까지는 높이가 안 변해도 기다려줌

        while True:
            # 1. 스크롤 내리기 (네이버는 끝까지 내리는 게 확실함)
            # 약간의 랜덤성을 주어 사람이 내리는 척합니다.
            scroll_amount = random.randint(800, 1200)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            
            # 2. 로딩 대기 (네이버는 구글보다 로딩이 조금 더 느릴 수 있음)
            time.sleep(random.uniform(1.0, 2.5))
            
            # 3. 현재 높이 측정
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # [핵심 수정 부분] 높이 비교 로직 개선
            if new_height == last_height:
                # 높이가 안 변했다면 바로 끝내지 말고 카운트를 올림
                retries += 1
                print(f"[로딩 대기 중...] 높이 변화 없음 ({retries}/{max_retries})")
                
                # 네이버의 트리거를 위해 살짝 위로 올렸다가 다시 내리는 "꿈틀" 동작 추가
                self.driver.execute_script("window.scrollBy(0, -300);")
                time.sleep(1)
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2) # 한번 더 기다림
                
                # 높이를 다시 갱신해서 확인
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                if portal == 'bing' and retries == 2 and img_counter == 0:
                    element = self.driver.find_element(By.CSS_SELECTOR, '#bop_container > div.mm_seemore > a')
                    self.driver.execute_script(f"arguments[{img_counter}].click();", element)
                    img_counter+=1

                # 여전히 안 변했고, 재시도 횟수가 찼다면 종료
                if new_height == last_height and retries >= max_retries:
                    print("더 이상 불러올 이미지가 없습니다. 스크롤 종료.")
                    break
                

            else:
                # 높이가 변했다면(새 이미지가 로딩됨) 카운트 초기화 및 계속 진행
                retries = 0 
                last_height = new_height
    
    def naver_parse(self, url) -> list:
        '''
        네이버의 경우 원본 사진을 리사이징해 썸네일, 2차 썸네일로 사용함
        확장자 뒤에서 끊고 request하면 원본사진을 손쉽게 얻을 수 있다.
        네이버 사진 갯수 1회 500개
        '''
        url_data = []
        self.driver.get(url)

        self.human_scroll_naver('naver')

        soup = BeautifulSoup(self.driver.page_source,'html.parser')

        raw_data = soup.select(f'#main_pack > section > div.api_subject_bx._fe_image_tab_grid_root.ani_fadein > div > div > div.image_tile._fe_image_tab_grid > div > div > div > div > img')
        for i, data in enumerate(raw_data):
            try:
                src = data.get('src')
                if not src:
                    src = data.get('data-src')

                if src.split(':')[0] == 'https':
                    url_data.append(src.split('&')[0])
            except:
                print(f'{i}번째 데이터 손실')

        return url_data
    
    def bing_parse(self, url) -> list:
        self.driver.get(url)

        self.human_scroll_naver('bing')

        soup = BeautifulSoup(self.driver.page_source,'html.parser')
        #soup = BeautifulSoup(requests.get(url).text,'html.parser')

        img_url=[]
        url_data = soup.find_all('div',{'class':'imgpt'})
        for data in url_data:
            tag_a = data.select_one('a')
            img_json = json.loads(tag_a['m'])
            #print(img_json['murl'])
            img_url.append(img_json['murl'])
        return img_url

    def file_save(self, target:list, dir:str):
        save_dir = dir

        with open('./asset/k2/marker.txt', 'r', encoding='utf-8') as t:
            data = t.readlines()

        start_num = int(data[0].split('=')[1])

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        for i, url in enumerate(target):
            try:
                # 이미지 요청
                response = requests.get(url, headers=headers, timeout=10)
                
                # 요청 성공 시 (상태코드 200) 저장
                if response.status_code == 200:
                    # 파일 경로 및 이름 설정 (예: downloaded_images/image_0.jpg)
                    file_path = os.path.join(save_dir, f'image_{start_num + i}.jpg')
                    
                    # 'wb'는 바이너리 쓰기 모드 (이미지, 동영상 등)
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    
                    print(f'{i}번째 이미지 저장 완료: {file_path}')
                else:
                    print(f'{i}번째 요청 실패: 상태 코드 {response.status_code}')
                    
            except Exception as e:
                print(f'{i}번째 에러 발생: {e}')

        with open('./asset/k2/marker.txt', 'w', encoding='utf-8') as t:
            save_num = start_num + len(target)
            t.write(f'num={save_num}')

if __name__ == "__main__":
    p = parser()
    data = p.naver_parse('https://search.naver.com/search.naver?ssc=tab.image.all&where=image&query=k1%EC%A0%84%EC%B0%A8+-%EC%A0%9C%EC%9E%91+-%EB%AA%A8%EB%8D%B8+-1%2F+-1%3A+-%EB%AA%A8%ED%98%95&sm=tab_dgs&qdt=1')
    #data = p.bing_parse('https://www.bing.com/images/search?q=K2+%ED%9D%91%ED%91%9C+%EC%A0%84%EC%B0%A8&form=QBIR&first=1&cw=2127&ch=1559')
    p.file_save(data, './asset/k2/')