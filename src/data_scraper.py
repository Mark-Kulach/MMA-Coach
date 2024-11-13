import time
import psycopg2
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from psycopg2 import sql

import re
import pickle
import os

# FIX: fill in gaps

def login_fight_pass(bot):
    bot.get('https://ufcfightpass.com/login/')
    
    cookies = WebDriverWait(bot, 10).until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
    cookies.click()

    username_input = WebDriverWait(bot, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='email']")))
    password_input = WebDriverWait(bot, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='password']")))

    username_input.clear()
    username_input.send_keys("mark@markkulach.com")
    password_input.clear()
    password_input.send_keys("3TJBiKqvXzJ!H9s")

    login_button = WebDriverWait(bot, 2).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
    login_button.click()

    time.sleep(10)


def scrape_event_footage(bot):
    login_fight_pass(bot)

    data = []

    bot.get("https://ufcfightpass.com/season/24054")
    while True:
        command = input("DONE:")

        if command == "":

            for event in bot.find_elements(By.XPATH, "//a[contains(@href, '/video/')]"):
                title = event.find_element(By.CLASS_NAME, "card-side__title").text.replace("vs ", "vs.").strip().lower()
                link = event.get_attribute("href")

                data.append({"title": title, "video_link": link})
        else:
            break

    return data


def scrape_fighters():
    # FIX: outline function
    
    pass


def scrape_fights(bot):
    actions = ActionChains(bot)
    login_fight_pass(bot)

    cursor = connect_to_db()[1]

    cursor.execute("SELECT id, video_link FROM events")
    rows = {row[0]: row[1] for row in cursor.fetchall()}

    output = []
    title_counts = {} 

    for id, video_link in rows.items():
        bot.get(video_link)
        time.sleep(5)

        try: 
            hover_element = bot.find_element(By.XPATH, "//div[@class='ds-replay-player']")

            actions.move_to_element(hover_element).perform()
        except NoSuchElementException:
            print("hover: " + str(id))
            
        try:
            fight_card = bot.find_element(By.XPATH, "//div[@class='tab-wrapper tab-wrapper__fightCards hidden-xs']")
            fight_card.find_element(By.TAG_NAME, "a").click()
        except NoSuchElementException:
            print("fight_card: " + str(id))

        time.sleep(2)
        fights = bot.find_elements(By.XPATH, "//div[@class='versus']")
        fights.reverse()
        fights = [fight.find_elements(By.XPATH, ".//div[@class='versus__competitor-meta']") for fight in fights]

        for i in range(len(fights)):
            fight = fights[i]

            for j in range(len(fight)):
                fighter_data = fight[j]
                h2_elements = fighter_data.find_elements(By.TAG_NAME, "h2")
                combined_text = " ".join(h2.text.lower() for h2 in h2_elements)

                fights[i][j] = combined_text

            fight.sort()
            fights[i] = f"{fight[0]} vs. {fight[1]}"

            title = fights[i]
            
            if title in title_counts:
                title_counts[title] += 1
                title += f" {title_counts[title]}"
            else:
                title_counts[title] = 1
            
            output.append({"event_id": id, "title": title})
    
    return output


def insert_data_to_table(table_name, data_list):
    conn, cursor = connect_to_db()

    columns = data_list[0].keys()
    insert_query = sql.SQL("INSERT INTO {table} ({fields}) VALUES ({values})").format(
        table=sql.Identifier(table_name),
        fields=sql.SQL(', ').join(sql.Identifier(col) for col in columns),
        values=sql.SQL(', ').join(sql.Placeholder() * len(columns)))
        
    for data in data_list:
        cursor.execute(insert_query, tuple(data[col] for col in columns))
    
    
    cursor.close()
    conn.close()


def connect_to_db():
    if os.name == "nt":
        DB_HOST = input("HOST:") + ".tcp.ngrok.io"
        DB_PORT = input("PORT:")

    else:
        DB_HOST = 'localhost'
        DB_PORT = 5432
    DB_NAME = 'mma_coach'
    DB_USER = 'postgres'

    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, port=DB_PORT)
    conn.autocommit = True
    cursor = conn.cursor()
    
    return conn, cursor


def scrape_links(bot):

    conn, cursor = connect_to_db()

    bot.get("http://ufcstats.com/statistics/events/completed?page=all")

    time.sleep(5)

    events = bot.find_elements(By.XPATH, "//a[contains(@href, '/event-details/')]")


    for event in events:
        title = event.text.strip().lower()
        stats_link = event.get_attribute("href")

        try: 
            if re.match(r"^UFC \d+:", title):
                title = title.split(":")[0] + ":"
            else:
                title = title.split(":")[1].replace("vs ", "vs.").strip().lower()
                
            cursor.execute("UPDATE events SET stats_link = %s WHERE title LIKE %s", (stats_link, f"%{title}%")) 

        except:
            pass

    conn.close()
    cursor.close()


def scrape_stats(bot):
    # FIX: pull stats_link from fights table
    # FIX: 
    cursor = connect_to_db()[1]

    event_data = []
    cursor.execute("SELECT id, stats_link FROM events")
    rows = {row[0]: row[1] for row in cursor.fetchall()}  

    for id, link in rows.items():
        bot.get(link)
        time.sleep(2)

        fights = []
        fight_urls = [el.get_attribute('data-link') for el in bot.find_elements(By.XPATH, "//td[@style='width:100px']/..")]
        
        for url in fight_urls:
            fight_data = {"event_id": id}
            bot.get(url)
            time.sleep(2)

            fighter_el = bot.find_elements(By.XPATH, "//a[@class='b-link b-fight-details__person-link']")
            fighters = [el.text for el in fighter_el]
            fighters.sort()
            title = f"{fighters[0]} vs. {fighters[1]}"

            fight_data["title"] = title

            outcome = "no contest"
            for el in fighter_el:
                txt = el.find_element(By.XPATH, "../../../i").text
                if txt == "W":
                    outcome = "winner: " + el.text
                elif txt == "D":
                    outcome = "draw" 
            
            fight_data["outcome"] = outcome
                        
            els = bot.find_elements(By.XPATH, "//i[contains(@class, 'b-fight-details__text-item')]")
            final_stats = [el.text for el in els]

            for i in range(len(final_stats)):
                if final_stats[i][-1] == ":":
                    final_stats[i] = els[i].find_element(By.XPATH, "..").text

            new = {}
            for item in final_stats:
                try:
                    if item.split(": ")[0].lower() == "details" and "decision" in new["method"]:
                        new[item.split(": ")[0].lower()] = "NA"
                    else:
                        new[item.split(": ")[0].lower()] = item.split(": ")[1].lower()

                except IndexError:
                    pass

            final_stats = new
            final_stats["end_time"] = final_stats.pop("time")
            fight_data.update(final_stats)

            for toggle in bot.find_elements(By.XPATH, "//a[@class='b-fight-details__collapse-link_rnd js-fight-collapse-link']"):
                toggle.click()

            data_rows = "//thead[@class='b-fight-details__table-row b-fight-details__table-row_type_head']/following-sibling::*[1]/tr"
            data_rows = bot.find_elements(By.XPATH, data_rows)
            data_rows = [row.find_elements(By.TAG_NAME, "td") for row in data_rows]

            for i in range(len(data_rows)):
                for j in range(len(data_rows[i])):
                    data_rows[i][j] = tuple(p.text for p in data_rows[i][j].find_elements(By.TAG_NAME, "p"))

            num_rounds = len(data_rows) // 2
            totals = data_rows[:num_rounds]
            strikes = data_rows[num_rounds:]

            headers_totals = [None, "kd", "sig_strikes", None, "tot_strikes", "td", None, "sub_att", "rev", "ctrl"]
            headers_strikes = [None, None, None, "head", "body", "leg", "distance", "clinch", "ground"]

            fighter_1 = []
            fighter_2 = []
            for i in range(2):
                name = totals[0][0][i]
    
                for round in range(len(totals)):
                    temp = {}
                    for stat in range((len(headers_totals))):
                        if headers_totals[stat] is not None:
                            ok = format_stat(totals[round][stat][i])
                            if isinstance(ok, tuple):
                                temp[headers_totals[stat]] = ok[0]
                                temp[headers_totals[stat] + "_att"] = ok[1]
                            else:
                                temp[headers_totals[stat]] = ok

                    for stat in range((len(headers_strikes))):
                        if headers_strikes[stat] is not None:
                            ok = format_stat(strikes[round][stat][i])
                            if isinstance(ok, tuple):
                                temp[headers_strikes[stat]] = ok[0]
                                temp[headers_strikes[stat] + "_att"] = ok[1]
                            else:
                                temp[headers_strikes[stat]] = ok

                    if fighters.index(name) == 0:
                        fighter_1.append(temp)
                    else:
                        fighter_2.append(temp)

            fight_data["fighter_1"] = fighter_1
            fight_data["fighter_2"] = fighter_2

            fights.append(fight_data)
        event_data.append(fights)
    return event_data


def format_stat(stat):
        if "of" in stat:
            stat = stat.split(" of ")
            stat = (int(stat[0]), int(stat[1]))

        elif ":" in stat:
            pass

        elif stat == "--":
            stat = "0:00"
        
        else: 
            stat = int(stat)

        return stat


def push_stats(data):
    conn, cursor = connect_to_db()

    try:
        for event_data in data:
            for fight_data in event_data:
                base_title = fight_data.get('title', 'Unknown Fight')
                fight_title = base_title
                counter = 2
                
                while True:
                    cursor.execute("SELECT COUNT(*) FROM fights WHERE title = %s", (fight_title,))
                    count_result = cursor.fetchone()
                    count = count_result[0] if count_result else 0
                    
                    if count == 0:
                        break
                    else:
                        fight_title = f"{base_title} {counter}"
                        counter += 1
                

                cursor.execute("""
                    INSERT INTO fights (event_id, title, outcome, method, details, round, end_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (fight_data.get("event_id", None), 
                      fight_title, 
                      fight_data.get("outcome", "unknown"), 
                      fight_data.get("method", "unknown"),
                      fight_data.get("details", "N/A"),
                      fight_data.get("round", 0), 
                      fight_data.get("end_time", "00:00")))

                fight_id_result = cursor.fetchone()
                fight_id = fight_id_result[0] if fight_id_result else None

                if fight_id is None:
                    print("Error: Fight ID not retrieved correctly.")
                    continue

                for i in ("1", "2"):
                    for round_num, round_data in enumerate(fight_data.get("fighter_" + i, [])):
                        cursor.execute("""
                            INSERT INTO stats (fight_id, round, fighter, kd, sig_strikes, sig_strikes_att, tot_strikes, 
                                tot_strikes_att, td, td_att, sub_att, rev, ctrl, head, head_att, body, body_att, leg, 
                                leg_att, distance, distance_att, clinch, clinch_att, ground, ground_att)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (fight_id, round_num + 1, int(i),
                              round_data.get("kd", 0),
                              round_data.get("sig_strikes", 0),
                              round_data.get("sig_strikes_att", 0),
                              round_data.get("tot_strikes", 0),
                              round_data.get("tot_strikes_att", 0),
                              round_data.get("td", 0),
                              round_data.get("td_att", 0),
                              round_data.get("sub_att", 0),
                              round_data.get("rev", 0),
                              round_data.get("ctrl", "0:00"),
                              round_data.get("head", 0),
                              round_data.get("head_att", 0),
                              round_data.get("body", 0),
                              round_data.get("body_att", 0),
                              round_data.get("leg", 0),
                              round_data.get("leg_att", 0),
                              round_data.get("distance", 0),
                              round_data.get("distance_att", 0),
                              round_data.get("clinch", 0),
                              round_data.get("clinch_att", 0),
                              round_data.get("ground", 0),
                              round_data.get("ground_att", 0)
                             ))

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        cursor.close()
        conn.close()


def merge_dictionaries(list1, list2, shared_key):
    merged_list = []
    dict2_lookup = {d[shared_key]: d for d in list2}

    for dict1 in list1:
        if dict1[shared_key] in dict2_lookup:
            merged_dict = {**dict1, **dict2_lookup[dict1[shared_key]]}
            merged_list.append(merged_dict)

    return merged_list


def main():
    driver = webdriver.Chrome()
    scrape_links(driver)
        

if __name__ == "__main__":
    main()