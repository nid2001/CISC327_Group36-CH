from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import random


def test_registration():
    driver = webdriver.Chrome()
    driver.get("http://127.0.0.1:5000/register")
    username = f"test_user_{random.randint(1000, 9999)}"  # 随机生成用户名
    password = "test_password"
    phone = "1234567890"

    try:
        # 填写注册信息
        driver.find_element(By.NAME, "phone").send_keys(phone)
        driver.find_element(By.NAME, "username").send_keys(username)
        driver.find_element(By.NAME, "email").send_keys(f"{username}@example.com")
        driver.find_element(By.NAME, "password").send_keys(password)

        # 设置用户类型为房东 (landlord)
        driver.find_element(By.CSS_SELECTOR, "input[name='user_type'][value='landlord']").click()

        # 提交注册
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # 验证注册成功
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
        print(f"Test Registration: PASSED (username: {username}, password: {password})")
    except Exception as e:
        print("Test Registration: FAILED")
        print(e)
    finally:
        driver.quit()

    return username, password, phone  # 返回生成的账号信息


def test_login(username, password):
    driver = webdriver.Chrome()
    driver.get("http://127.0.0.1:5000/login")

    try:
        # 填写登录信息
        driver.find_element(By.NAME, "username").send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # 验证登录成功
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
        print("Test Login: PASSED")
    except Exception as e:
        print("Test Login: FAILED")
        print(e)
    finally:
        driver.quit()


def test_logout(username, password, phone):
    driver = webdriver.Chrome()
    driver.get("http://127.0.0.1:5000/login")

    try:
        # 登录
        driver.find_element(By.NAME, "username").send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password)
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # 验证登录成功并跳转到主页面
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button[onclick=\"navigateTo('myaccount')\"]"))
        )
        print("Login: PASSED")

        # 点击“My Account”按钮
        my_account_button = driver.find_element(By.CSS_SELECTOR, "button[onclick=\"navigateTo('myaccount')\"]")
        my_account_button.click()

        # 验证进入“My Account”页面
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "form[action='/logout'] button"))
        )
        print("Navigated to My Account: PASSED")

        # 点击“Logout”按钮
        logout_button = driver.find_element(By.CSS_SELECTOR, "form[action='/logout'] button")
        logout_button.click()

        # 验证是否跳转到登出后的首页
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
        assert "Rental Management System" in driver.page_source, "Logout failed or incorrect page displayed"
        print("Logout: PASSED")

        # 验证“Login”链接是否存在
        login_link = driver.find_element(By.CSS_SELECTOR, "a[href='/login']")
        assert login_link.is_displayed(), "Login link not found after logout"

        # 可选：点击“Login”链接并验证跳转到登录页面
        login_link.click()
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        print("Navigated to Login Page: PASSED")

    except Exception as e:
        print("Test Logout: FAILED")
        print(e)
        print("Current Page Source:", driver.page_source)
    finally:
        driver.quit()
if __name__ == "__main__":
    print("Starting End-to-End Tests...")
    # 第一步：注册用户并获取账号信息
    username, password, phone = test_registration()

    # 第二步：登录使用注册的账号
    test_login(username, password)

    # 第三步：登出
    test_logout(username, password, phone)

    print("All Tests Completed Successfully!")