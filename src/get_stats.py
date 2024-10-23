import psycopg2
import time
from selenium import webdriver
from selenium.webdriver.common.by import By


def connect_to_db():
    DB_HOST = 'localhost'
    DB_PORT = 5432
    DB_NAME = 'mma_coach'
    DB_USER = 'postgres'

    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, port=DB_PORT)
    cursor = conn.cursor()
    
    return conn, cursor


def pull_events():
    
    conn, cursor = connect_to_db()
    
    cursor.execute(f"SELECT title FROM events")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return [row[0] for row in rows]    


def get_stats(driver):
    driver.get("http://ufcstats.com/statistics/events/completed?page=all")

    time.sleep(2)
    events = list(reversed(driver.find_elements(By.XPATH, "//a[contains(@href, 'ufcstats.com/event-details')]")))
    events = {element.text: element.get_attribute("href") for element in events if element.text in pull_events()}


    for link in events.values():
        driver.get(link)
        time.sleep(2)

        fights = []
        fight_urls = [el.get_attribute('data-link') for el in driver.find_elements(By.XPATH, "//td[@style='width:100px']/..")]
        
        for url in fight_urls:
            driver.get(url)
            time.sleep(2)

            fighter_el = driver.find_elements(By.XPATH, "//a[@class='b-link b-fight-details__person-link']")
            fighters = [el.text for el in fighter_el]
            fighters.sort()
            title = f"{fighters[0]} vs. {fighters[1]}"

            fight_data = {"title": title}

            del fighters

            winner = None
            for el in fighter_el:
                if el.find_element(By.XPATH, "../../../i").text == "W":
                    winner = el.text
            
            del fighter_el
            
            
            els = driver.find_elements(By.XPATH, "//i[contains(@class, 'b-fight-details__text-item')]")
            final_stats = [el.text for el in els]

            for i in range(len(final_stats)):
                if final_stats[i][-1] == ":":
                    final_stats[i] = els[i].find_element(By.XPATH, "..").text
            del els, i, el

            final_stats = {item.split(": ")[0].lower(): item.split(": ")[1].lower() for item in final_stats[:3]}
            final_stats["end_time"] = final_stats.pop("time")
            fight_data.update(final_stats)

            for toggle in driver.find_elements(By.XPATH, "//a[@class='b-fight-details__collapse-link_rnd js-fight-collapse-link']"):
                toggle.click()
            del toggle

            data_rows = "//thead[@class='b-fight-details__table-row b-fight-details__table-row_type_head']/following-sibling::*[1]/tr"
            data_rows = driver.find_elements(By.XPATH, data_rows)
            data_rows = [row.find_elements(By.TAG_NAME, "td") for row in data_rows]

            for i in range(len(data_rows)):
                for j in range(len(data_rows[i])):
                    data_rows[i][j] = tuple(p.text for p in data_rows[i][j].find_elements(By.TAG_NAME, "p"))
            del i, j

            num_rounds = len(data_rows) // 2
            totals = data_rows[:num_rounds]
            strikes = data_rows[num_rounds:]
            del data_rows, num_rounds

            headers_totals = [None, "kd", "sig_strikes", None, "tot_strikes", "td", None, "sub_att", "rev", "ctrl"]
            headers_strikes = [None, None, None, "head", "body", "leg", "distance", "clinch", "ground"]

            winner_stats = []
            loser_stats = []
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

                    if name == winner:
                        winner_stats.append(temp)
                        fight_data["winner"] = name
                    else:
                        loser_stats.append(temp)
                        fight_data["loser"] = name

            fight_data["winner_stats"] = winner_stats
            fight_data["loser_stats"] = loser_stats

            del headers_strikes, headers_totals, final_stats, i, stat, round, name, winner, strikes, totals, title, winner_stats, loser_stats

            fights.append(fight_data)
        return fights


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
    conn, cursor = connect_to_db()
    for fight_data in data:
        base_title = fight_data['title']
        fight_title = base_title
        counter = 1

        while True:
            cursor.execute("""
                SELECT COUNT(*) FROM fights WHERE title = %s
            """, (fight_title,))
            count = cursor.fetchone()[0]

            if count == 0:
                break
            else:
                fight_title = f"{base_title} {counter}"
                counter += 1

        cursor.execute("""
            INSERT INTO fights (title, winner, method, round, end_time)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (fight_title, fight_data['winner'], fight_data['method'], fight_data['round'], fight_data['end_time']))

        fight_id = cursor.fetchone()[0]

        for round in range(len(fight_data["winner_stats"])):
            w = fight_data["winner_stats"][round]

            cursor.execute("""
                    INSERT INTO stats (fight_id, round, winner, sig_strikes, sig_strikes_att, tot_strikes, tot_strikes_att, td, td_att, sub_att, rev, ctrl, head, head_att, body, body_att, leg, leg_att, distance, distance_att, clinch, clinch_att, ground, ground_att)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (fight_id, 
                      round + 1, 
                      True,
                      w["sig_strikes"],
                      w["sig_strikes_att"],
                      w["tot_strikes"],
                      w["tot_strikes_att"],
                      w["td"],
                      w["td_att"],
                      w["sub_att"],
                      w["rev"],
                      w["ctrl"],
                      w["head"],
                      w["head_att"],
                      w["body"],
                      w["body_att"],
                      w["leg"],
                      w["leg_att"],
                      w["distance"],
                      w["distance_att"],
                      w["clinch"],
                      w["clinch_att"],
                      w["ground"],
                      w["ground_att"])
            )

        
        for round in range(len(fight_data["loser_stats"])):
            l = fight_data["loser_stats"][round]

            cursor.execute("""
                    INSERT INTO stats (fight_id, round, winner, sig_strikes, sig_strikes_att, tot_strikes, tot_strikes_att, td, td_att, sub_att, rev, ctrl, head, head_att, body, body_att, leg, leg_att, distance, distance_att, clinch, clinch_att, ground, ground_att)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (fight_id, 
                      round + 1, 
                      False, 
                      l["sig_strikes"],
                      l["sig_strikes_att"],
                      l["tot_strikes"],
                      l["tot_strikes_att"],
                      l["td"],
                      l["td_att"],
                      l["sub_att"],
                      l["rev"],
                      l["ctrl"],
                      l["head"],
                      l["head_att"],
                      l["body"],
                      l["body_att"],
                      l["leg"],
                      l["leg_att"],
                      l["distance"],
                      l["distance_att"],
                      l["clinch"],
                      l["clinch_att"],
                      l["ground"],
                      l["ground_att"])
            )

    conn.commit()
    cursor.close()
    conn.close()


def main():
    driver = webdriver.Chrome()
    push_to_db(get_stats(driver))
    

if __name__ == "__main__":
    main()