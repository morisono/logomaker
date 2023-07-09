import os
import time
import zipfile
import streamlit as st
import pandas as pd
from rocketry import Rocketry
from rocketry.log import MinimalRecord
from redbird.repos import CSVFileRepo
from playwright.sync_api import sync_playwright
from rocketry.conds import every, cron, after_success
# from rocketry.conds import every, cron, after_success, time_of_day, monthly, weekly, daily, hourly, minutely, true, false


repo = CSVFileRepo(filename="tasks.csv", model=MinimalRecord)
app = Rocketry(logger_repo=repo, config={
    'task_execution': 'process',
    'task_pre_exist': 'raise',
    'force_status_from_logs': True,

    'silence_task_prerun': False,
    'silence_task_logging': False,
    'silence_cond_check': False,

    'max_process_count': 5,
    'restarting': 'replace',
    'cycle_sleep': 0.1
})

widget_control = st.sidebar.expander("Control", expanded=True)
with widget_control:
    interval_rule_name = ["every", "cron", "after_success"]
    interval = {
        'rule': st.selectbox('Enter interval rule:', interval_rule_name),
        'value': st.text_input('interval value:', value="5 seconds")
    }

selected_interval = ""
if interval['rule'] == "every":
    selected_interval = every(interval['value'])
if interval['rule'] == "cron":
    selected_interval = cron(interval['value'])
if interval['rule'] == "after_success":
    selected_interval = after_success(interval['value'])

def create_zip(zip_path, filelist):
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file in filelist:
            zipf.write(file, os.path.basename(file))

def run_periodically(temp_dir, url, locator, action, widget_control, main_pane, run_job, stop_job, df):
    with sync_playwright() as playwright:
        # webkit = playwright.webkit
        # iphone = playwright.devices["iPhone 6"]
        browser = playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-infobars"],
            slow_mo=1000
        )
        context = browser.new_context(
            record_video_dir="./videos",
            record_video_size={"height": 768, "width": 1024},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36",
            locale="en-US",
            timezone_id="America/New_York",
            viewport={"width": 1280, "height": 800}
        )
        page = browser.new_page()
        output_paths = []
        with widget_control:
            output_database = st.text_input('Enter output database path:', f"{temp_dir}/database.csv")
            # record_video = st.checkbox('Screen Record', True)
            # if record_video:
            #     rec_path = "./screen_record.mp4"
            #     page.video.path()

        widget_result = st.sidebar.expander("Result", expanded=True)
        with widget_result:
            side_pane = st.empty()

        if run_job:
            timestamp = time.strftime("%Y%m%d-%H%M%S")

            output_media = f"{temp_dir}/media/{timestamp}.png"

            element = None

            page.goto(url)

            if locator is not None:
                if locator['css_selector']:
                    element = page.query_selector(locator['css_selector'])
                elif locator['xpath']:
                    element = page.query_selector(locator['xpath'])
                elif locator['input_text']:
                    element = page.query_selector(locator['input_text'])
                elif locator['class_name']:
                    element = page.query_selector(locator['class_name'])

            if element:
                if action == 'Click':
                    element.click()
                    page_title = page.title
                    page_url = page.url
                    row = {'Action': action, 'Name': page_title, 'Value': page_url}

                    # time.sleep(1)

                    if page.is_download_done:
                        file_name = page.context._downloads._downloads[0].path
                        file_url = page.context._downloads._downloads[0].url
                        row['Name'] = file_name
                        row['URL'] = file_url

                    df = df.append(row, ignore_index=True)
                    main_pane.write(df)

                elif action == 'Fill':
                    element.fill(locator['input_text'])
                    page_title = page.title
                    page_url = page.url
                    row = {'Action': action, 'Name': page_title, 'Value': page_url}
                    df = df.append(row, ignore_index=True)
                    main_pane.write(df)

                elif action == 'Type':
                    element.type(locator['input_text'])
                    page_title = page.title
                    page_url = page.url
                    row = {'Action': action, 'Name': page_title, 'Value': page_url}
                    df = df.append(row, ignore_index=True)
                    main_pane.write(df)

                elif action == 'Press':
                    element.press(locator['input_text'])
                    page_title = page.title
                    page_url = page.url
                    row = {'Action': action, 'Name': page_title, 'Value': page_url}
                    df = df.append(row, ignore_index=True)
                    main_pane.write(df)

                elif action == 'Scroll':
                    element.scrollIntoViewIfNeeded()
                    page_title = page.title
                    page_url = page.url
                    row = {'Action': action, 'Name': page_title, 'Value': page_url}
                    df = df.append(row, ignore_index=True)
                    main_pane.write(df)

                elif action == 'Get attribute':
                    attribute_name = st.text_input('Enter attribute name:')
                    attribute_value = element.get_attribute(attribute_name)
                    st.write(f'The value of the attribute "{attribute_name}" is: {attribute_value}')
                    row = {'Action': action, 'Name': attribute_name, 'Value': attribute_value}
                    df = df.append(row, ignore_index=True)
                    main_pane.write(df)

                elif action == 'Take screenshot':
                    screenshot_path = output_media
                    element.screenshot(path=screenshot_path)
                    main_pane.image(screenshot_path)
                    row = {'Action': action, 'Name': f'{timestamp}', 'Value': f'{screenshot_path}'}
                    df = df.append(row, ignore_index=True)
                    df.to_csv(output_database, index=False)
                    output_paths.append(output_media)
            else:
                st.write('No element found with the specified locator.')

        elif stop_job:
            st.write("Job interpreted.")

        else:
            side_pane.table(df)
            # time.sleep(interval)
            context.close()
            browser.close()
            main_pane.video(page.video)

        if not df.empty:
            df.to_csv(output_database, index=False)
        return output_paths

@app.task(selected_interval)
def main():

    st.title('Simple Web Automator')
    temp_dir = 'outputs'
    main_pane = st.empty()
    with widget_control:
        url = st.text_input('Enter URL:', 'http://books.toscrape.com/')

        locator = {
            'css_selector': st.text_input('Enter CSS selector:', 'body'),
            'xpath': st.text_input('Enter XPath:', 'xpath=//input[@class="test1"]'),
            'input_text': st.text_input('Enter Tag name:', 'input.test1'),
            'class_name': st.text_input('Enter Class name:', '//input[@class="test1"]'),
        }

        action = st.selectbox('Select action:', ['Click', 'Fill', 'Type', 'Press', 'Scroll', 'Get attribute', 'Take screenshot'], 6)

        # interval = st.number_input('Enter time interval (in seconds):', value=10, min_value=1)

        run_job = st.button("Run")

        stop_job = st.button("Stop")

        df = pd.DataFrame(columns=['Action', 'Name', 'Value'])

        output_paths = []

    if run_job:
        # run_periodically = asyncio.create_task(app.serve())
        output_paths = run_periodically(temp_dir, url, locator, action, widget_control, main_pane, run_job, stop_job, df)

    if stop_job:
        st.write("Job stopped.")
        if st.button("Create Zip"):
            zip_fname = st.text_input('Zip name', 'output.zip')
            zip_path = os.path.join(temp_dir, zip_fname)
            create_zip(zip_path, output_paths)
            with open(zip_path, "rb") as file:
                st.download_button(
                    label="Download images (.zip)",
                    data=file,
                    file_name=zip_fname,
                    mime="application/zip"
                )


if __name__ == '__main__':
    main()