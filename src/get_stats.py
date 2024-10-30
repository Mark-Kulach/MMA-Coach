import psycopg2
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
import pickle   
import os

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
    cursor = conn.cursor()
    
    return conn, cursor


def pull_events():    
    cursor.execute("SELECT id, fight_link FROM events")
    rows = cursor.fetchall()

    return {row[0]: row[1] for row in rows}


def get_stats():
    event_data = []

    for id, link in pull_events().items():
        driver.get(link)
        time.sleep(2)

        fights = []
        fight_urls = [el.get_attribute('data-link') for el in driver.find_elements(By.XPATH, "//td[@style='width:100px']/..")]
        
        for url in fight_urls:
            fight_data = {"event_id": id}
            driver.get(url)
            time.sleep(2)

            fighter_el = driver.find_elements(By.XPATH, "//a[@class='b-link b-fight-details__person-link']")
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
                        
            els = driver.find_elements(By.XPATH, "//i[contains(@class, 'b-fight-details__text-item')]")
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

            for toggle in driver.find_elements(By.XPATH, "//a[@class='b-fight-details__collapse-link_rnd js-fight-collapse-link']"):
                toggle.click()

            data_rows = "//thead[@class='b-fight-details__table-row b-fight-details__table-row_type_head']/following-sibling::*[1]/tr"
            data_rows = driver.find_elements(By.XPATH, data_rows)
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

    else:
        stat = int(stat)

    return stat


def push_to_db(data):
    try:
        for event_data in data:
            for fight_data in event_data:
                # Check and set defaults for missing keys in fight_data
                base_title = fight_data.get('title', 'Unknown Fight')
                fight_title = base_title
                counter = 2
                
                # Check for duplicates and create a unique title if needed
                while True:
                    cursor.execute("SELECT COUNT(*) FROM fights WHERE title = %s", (fight_title,))
                    count_result = cursor.fetchone()
                    count = count_result[0] if count_result else 0  # Safe handling of fetchone()
                    
                    if count == 0:
                        break
                    else:
                        fight_title = f"{base_title} {counter}"
                        counter += 1
                

                # Insert fight data into the `fights` table
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
                conn.commit()

                # Retrieve the new fight ID for linking stats
                fight_id_result = cursor.fetchone()
                fight_id = fight_id_result[0] if fight_id_result else None

                if fight_id is None:
                    print("Error: Fight ID not retrieved correctly.")
                    continue

                # Loop over fighter stats (fighter_1, fighter_2)
                for i in ("1", "2"):
                    for round_num, round_data in enumerate(fight_data.get("fighter_" + i, [])):
                        # Insert round stats for each fighter
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
                        conn.commit()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        cursor.close()
        conn.close()



def main():
    global driver, conn, cursor
    conn, cursor = connect_to_db()
    if not os.path.exists("data.pkl"):

        driver = webdriver.Chrome()
        data = get_stats()
        with open("data.pkl", "wb") as file:
            pickle.dump(data, file)
        driver.quit()

    else:
        with open("data.pkl", "rb") as temp:
            data = pickle.load(temp)
        push_to_db(data)

if __name__ == "__main__":
    main()