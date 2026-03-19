from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
import queue
import aiohttp
import aiofiles
import asyncio
import time
import random
import requests
import os
import json
import threading

class parser:
    def __init__(self):
        options = Options()
        options.add_argument('window-size=1200,1000')
        self.driver = webdriver.Chrome(options=options)
        self.url_queue = queue.Queue()

        self.runningFlag=True

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
        specific_url=[]
        url_data = soup.find_all('div',{'class':'imgpt'})
        for data in url_data:
            tag_a = data.select_one('a')
            img_json = json.loads(tag_a['m'])
            #print(img_json['murl'])
            img_url.append(img_json['murl'])
            specific_url.append('https://www.bing.com'+tag_a['href'])
        # print(specific_url)
        return img_url, specific_url
    
    def bing_specific_parse(self, url) -> list:
        self.driver.get(url)
        time.sleep(1.5)

        #self.human_scroll_naver('bing')

        body = self.driver.find_element(By.CSS_SELECTOR, '#detailCanvas')
        #body.click()

        body.send_keys(Keys.PAGE_DOWN)
        time.sleep(1)
        body.send_keys(Keys.PAGE_DOWN)
        time.sleep(1.5)

        try:
            self.driver.find_element(By.XPATH, '//*[@id="detailCanvas"]/div[2]/div/ul/li[1]/div/div[2]/div/div').click()
        except:
            print('이미지 더보기 버튼 없음')
        for _ in range(15):
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(random.uniform(0.3,0.5))

        soup = BeautifulSoup(self.driver.page_source,'html.parser')
        #soup = BeautifulSoup(requests.get(url).text,'html.parser')
        #print(requests.get(url).text)
        img_url=[]
        url_data = soup.find_all('a', {'class':'richImgLnk'})
        #print(url_data)
        
        for data in url_data:
            img_json = json.loads(data['data-m'])
            img_url.append(img_json['murl'])
        return img_url

    def file_save(self, target:list, dir:str):
        save_dir = dir

        with open(f'{dir}marker.txt', 'r', encoding='utf-8') as t:
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

        with open(f'{dir}marker.txt', 'w', encoding='utf-8') as t:
            save_num = start_num + len(target)
            t.write(f'num={save_num}')

    async def download_image(self, session, url, file_name, semaphore):
        async with semaphore:
            try:
                timeout = aiohttp.ClientTimeout(total=7)
                async with session.get(url, timeout=timeout) as response:
                    if response.status == 200:
                        async with aiofiles.open(file_name, mode='wb') as f:
                            await f.write(await response.read())
                        print(f"[성공] {file_name} 다운로드 완료")
                    else:
                        print(f"[실패] {url} - 상태 코드: {response.status}")
            except Exception as e:
                print(f"[에러] {url} - {e}")

    async def download_all_images(self, url_list, save_dir):
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        with open(f'{save_dir}marker.txt', 'r', encoding='utf-8') as t:
            data = t.readlines()

        start_num = int(data[0].split('=')[1])

        semaphore = asyncio.Semaphore(50) 
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for idx, url in enumerate(url_list):
                file_name = os.path.join(save_dir, f"image_{start_num+idx}.jpg")
                
                task = asyncio.create_task(self.download_image(session, url, file_name, semaphore))
                tasks.append(task)
            await asyncio.gather(*tasks)

        with open(f'{save_dir}marker.txt', 'w', encoding='utf-8') as t:
            save_num = start_num + len(url_list)
            t.write(f'num={save_num}')

    def thread_handler(self):
        while self.runningFlag:
            if not self.url_queue.empty():
                url_list = self.url_queue.get()
                #print(url_list)
            else:
                time.sleep(0.01)
                continue
            
            asyncio.run(self.download_all_images(url_list, './asset/k2/'))
    
    def run_thread(self):
        save_thread = threading.Thread(target=self.thread_handler, daemon=True)
        save_thread.start()

if __name__ == "__main__":
    p = parser()
    total_url_list = []
    #data = p.naver_parse('https://search.naver.com/search.naver?ssc=tab.image.all&where=image&query=k1%EC%A0%84%EC%B0%A8+-%EC%A0%9C%EC%9E%91+-%EB%AA%A8%EB%8D%B8+-1%2F+-1%3A+-%EB%AA%A8%ED%98%95&sm=tab_dgs&qdt=1')
    data, specific_url = p.bing_parse('https://www.bing.com/images/search?q=K2+%ED%9D%91%ED%91%9C+%EC%A0%84%EC%B0%A8&form=QBIR&first=1&cw=2127&ch=1559')
    p.run_thread()
    p.url_queue.put(data)
    # asyncio.run(p.download_all_images(data, './asset/k2/'))
    length_url=len(specific_url)
    for i, spec in enumerate(specific_url):
        res_list = p.bing_specific_parse(spec)
        p.url_queue.put(res_list)
        print(f'{i}/{length_url}')
    
    
    # p.bing_specific_parse('https://www.bing.com/images/search?view=detailV2&ccid=SxPxzpRZ&id=FE5C78B4C6359AF8C0BF1121972B80DD0CD476EC&thid=OIP.SxPxzpRZHbY7IAVH1tea0AHaDn&mediaurl=https%3A%2F%2Fimg.hankyung.com%2Fphoto%2F202206%2FAA.30387090.1.jpg&exph=303&expw=620&q=k2+%EC%A0%84%EC%B0%A8&FORM=IRPRST&ck=832CD9BE63BB9BD87FE335959BBFE2B4&selectedIndex=3&itb=0&cw=1895&ch=1418&ajaxhist=0&ajaxserp=0')
    #p.file_save(data, './asset/k2/')