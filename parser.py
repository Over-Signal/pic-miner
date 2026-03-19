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
        self.file_num = -1
        self.options = Options()
        self.options.add_argument('window-size=1200,1000')
        #self.driver = webdriver.Chrome(options=options)
        self.pic_url_queue = queue.Queue()
        self.crawl_url_queue = queue.Queue()
        self.mutex = threading.Lock()

        self.runningFlag=True
    

    def human_scroll_naver(self, driver:webdriver.Chrome, portal:str):
        img_counter = 0
        last_height = driver.execute_script("return document.body.scrollHeight")
    
    # 멈춘 횟수를 카운트하는 변수
        retries = 0 
        max_retries = 3  # 최대 3번까지는 높이가 안 변해도 기다려줌

        while True:
            # 1. 스크롤 내리기 (네이버는 끝까지 내리는 게 확실함)
            # 약간의 랜덤성을 주어 사람이 내리는 척합니다.
            scroll_amount = random.randint(800, 1200)
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            
            # 2. 로딩 대기 (네이버는 구글보다 로딩이 조금 더 느릴 수 있음)
            time.sleep(random.uniform(1.0, 2.5))
            
            # 3. 현재 높이 측정
            new_height = driver.execute_script("return document.body.scrollHeight")
            
            # [핵심 수정 부분] 높이 비교 로직 개선
            if new_height == last_height:
                # 높이가 안 변했다면 바로 끝내지 말고 카운트를 올림
                retries += 1
                print(f"[로딩 대기 중...] 높이 변화 없음 ({retries}/{max_retries})")
                
                # 네이버의 트리거를 위해 살짝 위로 올렸다가 다시 내리는 "꿈틀" 동작 추가
                driver.execute_script("window.scrollBy(0, -300);")
                time.sleep(1)
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2) # 한번 더 기다림
                
                # 높이를 다시 갱신해서 확인
                new_height = driver.execute_script("return document.body.scrollHeight")
                
                if portal == 'bing' and retries == 2 and img_counter == 0:
                    element = driver.find_element(By.CSS_SELECTOR, '#bop_container > div.mm_seemore > a')
                    driver.execute_script(f"arguments[{img_counter}].click();", element)
                    img_counter+=1

                # 여전히 안 변했고, 재시도 횟수가 찼다면 종료
                if new_height == last_height and retries >= max_retries:
                    print("더 이상 불러올 이미지가 없습니다. 스크롤 종료.")
                    break
                

            else:
                # 높이가 변했다면(새 이미지가 로딩됨) 카운트 초기화 및 계속 진행
                retries = 0 
                last_height = new_height
    
    def naver_parse(self, driver:webdriver.Chrome, url) -> list:
        '''
        네이버의 경우 원본 사진을 리사이징해 썸네일, 2차 썸네일로 사용함
        확장자 뒤에서 끊고 request하면 원본사진을 손쉽게 얻을 수 있다.
        네이버 사진 갯수 1회 500개
        '''
        url_data = []
        driver.get(url)

        soup = BeautifulSoup(driver.page_source,'html.parser')

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
        driver = webdriver.Chrome(options=self.options)
        driver.get(url)

        self.human_scroll_naver(driver, 'bing')

        soup = BeautifulSoup(driver.page_source,'html.parser')
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
        driver.close()
        return img_url, specific_url
    
    def bing_specific_parse(self) -> list:
        driver = webdriver.Chrome(options=self.options)
        while self.runningFlag:
            if not self.crawl_url_queue.empty():
                url = self.crawl_url_queue.get()
            else:
                time.sleep(0.01)
                continue

            driver.get(url)
            time.sleep(1.5)

            #self.human_scroll_naver('bing')

            body = driver.find_element(By.CSS_SELECTOR, '#detailCanvas')
            #body.click()

            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(1)
            body.send_keys(Keys.PAGE_DOWN)
            time.sleep(1.5)

            try:
                driver.find_element(By.XPATH, '//*[@id="detailCanvas"]/div[2]/div/ul/li[1]/div/div[2]/div/div').click()
            except:
                print('이미지 더보기 버튼 없음')
            for _ in range(15):
                body.send_keys(Keys.PAGE_DOWN)
                time.sleep(random.uniform(0.3,0.5))

            soup = BeautifulSoup(driver.page_source,'html.parser')
            #soup = BeautifulSoup(requests.get(url).text,'html.parser')
            #print(requests.get(url).text)
            img_url=[]
            url_data = soup.find_all('a', {'class':'richImgLnk'})
            #print(url_data)
            
            for data in url_data:
                img_json = json.loads(data['data-m'])
                img_url.append(img_json['murl'])
            
            self.pic_url_queue.put(img_url)

    async def download_image(self, session, url, file_name, semaphore):
        async with semaphore:
            try:
                timeout = aiohttp.ClientTimeout(total=3)
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

        with self.mutex:
            with open(f'{save_dir}marker.txt', 'r', encoding='utf-8') as t:
                data = t.readlines()

            start_num = int(data[0].split('=')[1])

            with open(f'{save_dir}marker.txt', 'w', encoding='utf-8') as t:
                save_num = start_num + len(url_list)
                t.write(f'num={save_num}')

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

    def save_thread_handler(self):
        while self.runningFlag:
            if not self.pic_url_queue.empty():
                url_list = self.pic_url_queue.get()
                #print(url_list)
            else:
                time.sleep(0.01)
                continue
            
            asyncio.run(self.download_all_images(url_list, './asset/k1/'))
    
    def run_thread(self):
        save_thread_1 = threading.Thread(target = p.save_thread_handler, daemon=True)
        save_thread_2 = threading.Thread(target = p.save_thread_handler, daemon=True)
        save_thread_1.start()
        save_thread_2.start()

if __name__ == "__main__":
    NUM_CRAWL_THREAD = 3

    p = parser()
    crawl_thread = []
    
    #data = p.naver_parse('https://search.naver.com/search.naver?ssc=tab.image.all&where=image&query=k1%EC%A0%84%EC%B0%A8+-%EC%A0%9C%EC%9E%91+-%EB%AA%A8%EB%8D%B8+-1%2F+-1%3A+-%EB%AA%A8%ED%98%95&sm=tab_dgs&qdt=1')
    data, specific_url = p.bing_parse('https://www.bing.com/images/search?q=k1+tank&form=HDRSC3&first=1')

    p.run_thread()
    

    p.pic_url_queue.put(data)

    for data in specific_url:
        p.crawl_url_queue.put(data)

    for _ in range(NUM_CRAWL_THREAD):
        thread = threading.Thread(target=p.bing_specific_parse, daemon=True)
        thread.start()
        crawl_thread.append(thread)
    

    for t in crawl_thread:
        t.join()
    
    p.runningFlag = False

# est 1500img/min -> 3 crawl thread + 2 save thread

