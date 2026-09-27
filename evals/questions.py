evaluation_questions = [
    # --- FOOTBALL PROFILES ---
    {
        "user_input": "Which team uses aggressive high pressing?",
        "reference": "Bayern Munich uses aggressive high pressing with high intensity without the ball, forwards pressuring defenders quickly, and midfielders closing passing lanes.",
        "source_ids": ["football_profiles"],
    },
    {
        "user_input": "How does Arsenal build up play?",
        "reference": "Arsenal relies on structured possession from the back, with centre-backs comfortable under pressure, midfielders dropping into passing lanes, and full-backs moving into inverted positions.",
        "source_ids": ["football_profiles"],
    },
    {
        "user_input": "What are Real Madrid known for in the Champions League?",
        "reference": "Real Madrid are known for strong transitions, elite individual quality, fast counter-attacks, and experience in knockout Champions League matches.",
        "source_ids": ["football_profiles"],
    },
    {
        "user_input": "How does Manchester City play possession football?",
        "reference": "Manchester City focuses on positional play, patient buildup, short passing, overloads in midfield, and controlling territory with high defensive lines.",
        "source_ids": ["football_profiles"],
    },
    {
        "user_input": "What is Barcelona's possession style?",
        "reference": "Barcelona focuses on technical midfield control, positional rotations, short passing, and creating chances through central combinations with heavy ball retention.",
        "source_ids": ["football_profiles"],
    },
    {
        "user_input": "What are PSG's attacking strengths?",
        "reference": "PSG depends on pace, technical quality, direct attacking actions, and quick combinations in the final third, with wide attackers dangerous in one-versus-one situations.",
        "source_ids": ["football_profiles"],
    },

    # --- UEFA REPORT ---
    {
        "user_input": "What does the UEFA report say about Arsenal's pressing?",
        "reference": "The report notes Arsenal pressed PSG high from the first minute with a compact mid-block shape, using coordinated pressing with Bukayo Saka, William Saliba, and Jurriën Timber.",
        "source_ids": ["ucl_2025"],
    },
    {
        "user_input": "Which team had the most shots from counter-attacks in the UEFA report?",
        "reference": "Paris Saint-Germain averaged 1.8 shots from counter-attacks per game, the highest in the report.",
        "source_ids": ["ucl_2025"],
    },
    {
        "user_input": "What does the UEFA report say about Liverpool's pressing strategy?",
        "reference": "Liverpool caught the eye for their focused high press, specifically targeting Milan's left side with highly targeted pressing carried out with a clear purpose.",
        "source_ids": ["ucl_2025"],
    },
    {
        "user_input": "How does the report describe Paris Saint-Germain's defensive fundamentals?",
        "reference": "The report highlights PSG's defensive mobility, ability to defend one-on-one, and excellent positioning in the box, as noted by Henning Berg after their match against Liverpool.",
        "source_ids": ["ucl_2025"],
    },
    {
        "user_input": "What did Luis Enrique say about Arsenal after the match?",
        "reference": "Luis Enrique admitted that Arsenal pressed PSG high from the first minute and they couldn't overcome it.",
        "source_ids": ["ucl_2025"],
    },
    {
        "user_input": "Which teams excelled in counter-pressing according to the UEFA report?",
        "reference": "Manchester City led with 84% of counter-pressing actions in opposition territory, followed by Arsenal at 81%, Bayern at 80%, and Aston Villa at 78%.",
        "source_ids": ["ucl_2025"],
    },

    # --- MULTI-CONTEXT (single-source synthesis across multiple chunks/docs) ---
    {
        "user_input": "Compare how Arsenal and Manchester City press after losing the ball.",
        "reference": "Arsenal press by pushing their forwards onto the centre-backs and using midfielders to block central passing lanes, forcing opponents wide, then react quickly to win the ball back before a counter-attack. Manchester City counter-press immediately after losing possession to stop the opponent escaping and win the ball back close to goal, relying on a high defensive line and coordination between defenders and midfielders.",
        "source_ids": ["football_profiles"],
    },
    {
        "user_input": "According to the UEFA report, which team led in counter-pressing intensity and which team was most dangerous in transitions?",
        "reference": "Manchester City led counter-pressing intensity, with 84% of their counter-pressing actions taking place in the opposition half. Paris Saint-Germain were the most effective in transitions, averaging the most shots from counterattacks per game at 1.8.",
        "source_ids": ["ucl_2025"],
    },

    # --- CROSS-SOURCE / HARDER CASES ---
    {
        "user_input": "Compare how the general football profile explains high pressing with how Liverpool applied it against Milan in the UEFA report.",
        "reference": "The football profile explains high pressing as coordinated pressure high up the pitch to force mistakes, while the UEFA report shows Liverpool applying it in a targeted and purposeful way against Milan.",
        "source_ids": ["football_profiles", "ucl_2025"],
    },
    {
        "user_input": "What similarities exist between Bayern Munich's pressing style and Arsenal's pressing against Paris?",
        "reference": "Both involve aggressive pressure, coordinated movement, players stepping forward to close options, and attempts to stop the opponent from building attacks comfortably.",
        "source_ids": ["football_profiles", "ucl_2025"],
    },
    {
        "user_input": "What does the available knowledge base say about Inter Miami's pressing strategy?",
        "reference": "The available sources do not provide enough information about Inter Miami's pressing strategy.",
        "source_ids": ["football_profiles", "ucl_2025"],
    },
]