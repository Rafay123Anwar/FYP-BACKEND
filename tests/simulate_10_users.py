import asyncio
import io
import time
import uuid
import httpx

BASE_URL = "http://127.0.0.1:8000/api/v1"
RUN_ID = uuid.uuid4().hex[:8]

# Store test context
user_credentials = []
user_tokens = []
user_education_ids = {}
user_experience_ids = {}
user_resume_ids = {}
test_results = {}

# Minimal valid PDF binary mock
VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"


def print_header(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


async def test_scenario_a_concurrency_register(client: httpx.AsyncClient):
    """Scenario A: Register 10 distinct users concurrently."""
    print_header("SCENARIO A: Concurrent Registration of 10 Distinct Users")
    start = time.perf_counter()

    async def register_one(i: int):
        email = f"sim_user_{RUN_ID}_{i}@testats.com"
        password = f"StrongPass!{RUN_ID}_{i}"
        full_name = f"Candidate {RUN_ID} #{i}"
        payload = {
            "email": email,
            "password": password,
            "full_name": full_name,
            "role": "JOB_SEEKER",
        }
        res = await client.post("/auth/register", json=payload)
        return i, email, password, res

    tasks = [register_one(i) for i in range(1, 11)]
    responses = await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start

    success_count = 0
    for idx, email, password, res in responses:
        if res.status_code == 201:
            success_count += 1
            user_credentials.append({"idx": idx, "email": email, "password": password, "user_id": res.json()["id"]})
        else:
            print(f"  [X] User {idx} registration failed: {res.status_code} - {res.text}")

    status = "PASSED" if success_count == 10 else "FAILED"
    print(f"  Result: {success_count}/10 successful registrations in {elapsed:.3f}s -> {status}")
    test_results["Scenario A (Concurrent Registration)"] = {
        "status": status,
        "detail": f"{success_count}/10 registrations succeeded concurrently in {elapsed:.3f}s",
    }


async def test_scenario_b_race_condition(client: httpx.AsyncClient):
    """Scenario B: Register 3 users with the EXACT SAME email concurrently."""
    print_header("SCENARIO B: Race Condition on Duplicate Email Registration")
    shared_email = f"shared_race_{RUN_ID}@testats.com"
    payload = {
        "email": shared_email,
        "password": "Password123!",
        "full_name": "Racer Candidate",
        "role": "JOB_SEEKER",
    }

    start = time.perf_counter()
    tasks = [client.post("/auth/register", json=payload) for _ in range(3)]
    responses = await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start

    statuses = [r.status_code for r in responses]
    successes = [r for r in responses if r.status_code == 201]
    rejections = [r for r in responses if r.status_code == 400]

    correct_rejections = all("Email already registered" in r.text for r in rejections)
    passed = len(successes) == 1 and len(rejections) == 2 and correct_rejections
    status = "PASSED" if passed else "FAILED"

    print(f"  Responses received: {statuses}")
    print(f"  Exact outcomes: 201 Created: {len(successes)}, 400 Bad Request: {len(rejections)}")
    print(f"  Result in {elapsed:.3f}s -> {status}")
    test_results["Scenario B (Race Condition Protection)"] = {
        "status": status,
        "detail": f"Out of 3 parallel racers, exactly 1 succeeded and 2 were safely rejected with 400 ({elapsed:.3f}s)",
    }


async def test_scenario_c_concurrent_login(client: httpx.AsyncClient):
    """Scenario C: Log in the 10 registered users concurrently."""
    print_header("SCENARIO C: Concurrent Login for 10 Users & JWT Issuance")
    start = time.perf_counter()

    async def login_one(user):
        payload = {"email": user["email"], "password": user["password"]}
        res = await client.post("/auth/login", json=payload)
        return user["idx"], res

    tasks = [login_one(u) for u in user_credentials]
    responses = await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start

    login_success = 0
    for idx, res in responses:
        if res.status_code == 200 and "access_token" in res.json():
            login_success += 1
            user_tokens.append({"idx": idx, "token": res.json()["access_token"]})
        else:
            print(f"  [X] User {idx} login failed: {res.status_code} - {res.text}")

    status = "PASSED" if login_success == 10 else "FAILED"
    print(f"  Result: {login_success}/10 tokens issued concurrently in {elapsed:.3f}s -> {status}")
    test_results["Scenario C (Concurrent Login)"] = {
        "status": status,
        "detail": f"{login_success}/10 users logged in and obtained valid JWT tokens in {elapsed:.3f}s",
    }


async def test_scenario_d_profile_creation(client: httpx.AsyncClient):
    """Scenario D: Concurrently create Profile, Education, and Experience for 10 users."""
    print_header("SCENARIO D: Concurrent Profile, Education & Experience Creation")
    start = time.perf_counter()

    async def create_candidate_records(user_token_obj):
        idx = user_token_obj["idx"]
        token = user_token_obj["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Profile upsert
        p_res = await client.put(
            "/profile/",
            headers=headers,
            json={
                "headline": f"Software Engineer #{idx}",
                "summary": f"Experienced backend engineer #{idx} specializing in Python & async systems.",
                "location": "San Francisco, CA",
                "phone": f"+1-555-01{idx:02d}",
                "linkedin": f"https://linkedin.com/in/user{idx}",
            },
        )

        # 2. Education creation
        e_res = await client.post(
            "/profile/education",
            headers=headers,
            json={
                "institution": f"State Tech University #{idx}",
                "degree": "B.S. Computer Science",
                "field": "Software Engineering",
                "start_date": "2018-09-01",
                "end_date": "2022-05-31",
            },
        )
        edu_id = e_res.json().get("id") if e_res.status_code == 201 else None

        # 3. Experience creation
        x_res = await client.post(
            "/profile/experience",
            headers=headers,
            json={
                "company": f"Cloud Enterprise #{idx}",
                "job_title": "Backend Developer",
                "start_date": "2022-06-01",
                "description": "High-throughput API development",
            },
        )
        exp_id = x_res.json().get("id") if x_res.status_code == 201 else None

        return idx, p_res.status_code, e_res.status_code, x_res.status_code, edu_id, exp_id

    tasks = [create_candidate_records(u) for u in user_tokens]
    results = await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start

    all_success = True
    for idx, p_code, e_code, x_code, edu_id, exp_id in results:
        if p_code == 200 and e_code == 201 and x_code == 201:
            user_education_ids[idx] = edu_id
            user_experience_ids[idx] = exp_id
        else:
            all_success = False
            print(f"  [X] User {idx} record setup failure: Profile={p_code}, Edu={e_code}, Exp={x_code}")

    status = "PASSED" if all_success else "FAILED"
    print(f"  Result: 10 candidate profiles, educations, and experiences populated in {elapsed:.3f}s -> {status}")
    test_results["Scenario D (Profile Creation)"] = {
        "status": status,
        "detail": f"All 10 users populated full profile data (30 DB write operations) in {elapsed:.3f}s",
    }


async def test_scenario_e_ownership_security(client: httpx.AsyncClient):
    """Scenario E: Strict Data Ownership. User 1 tries to modify/delete User 2's data."""
    print_header("SCENARIO E: Data Ownership Enforcement (Cross-User ID Isolation)")
    user1 = user_tokens[0]
    user2 = user_tokens[1]
    u1_headers = {"Authorization": f"Bearer {user1['token']}"}

    u2_edu_id = user_education_ids[user2["idx"]]
    u2_exp_id = user_experience_ids[user2["idx"]]

    # 1. User 1 tries to PUT User 2's education
    put_res = await client.put(
        f"/profile/education/{u2_edu_id}",
        headers=u1_headers,
        json={"institution": "Hacked University"},
    )

    # 2. User 1 tries to DELETE User 2's experience
    del_res = await client.delete(
        f"/profile/experience/{u2_exp_id}",
        headers=u1_headers,
    )

    put_secure = put_res.status_code in (403, 404)
    del_secure = del_res.status_code in (403, 404)
    passed = put_secure and del_secure
    status = "PASSED" if passed else "FAILED"

    print(f"  User 1 unauthorized PUT User 2 Education: Status {put_res.status_code} (Expected 404/403)")
    print(f"  User 1 unauthorized DELETE User 2 Experience: Status {del_res.status_code} (Expected 404/403)")
    print(f"  Result -> {status}")
    test_results["Scenario E (Strict Ownership Validation)"] = {
        "status": status,
        "detail": f"Cross-tenant access attempts were blocked with {put_res.status_code} and {del_res.status_code}",
    }


async def test_scenario_f_invalid_file_validation(client: httpx.AsyncClient):
    """Scenario F: Validate reject of non-PDF/DOCX file formats."""
    print_header("SCENARIO F: Resume File Format & MIME Type Validation")
    user1 = user_tokens[0]
    headers = {"Authorization": f"Bearer {user1['token']}"}

    # Attempt to upload plain text file
    files = {"file": ("malicious_script.txt", io.BytesIO(b"echo hack"), "text/plain")}
    res = await client.post("/resumes/upload", headers=headers, files=files)

    passed = res.status_code == 400 and "Only PDF and DOCX files are allowed" in res.text
    status = "PASSED" if passed else "FAILED"

    print(f"  Upload of .txt file returned: {res.status_code} (Detail: {res.json().get('detail')})")
    print(f"  Result -> {status}")
    test_results["Scenario F (File Format Validation)"] = {
        "status": status,
        "detail": f"Invalid format correctly rejected with HTTP 400: '{res.json().get('detail')}'",
    }


async def test_scenario_g_concurrent_resume_uploads(client: httpx.AsyncClient):
    """Scenario G: Concurrently upload 10 valid resumes to Supabase Storage."""
    print_header("SCENARIO G: Concurrent Supabase Storage Cloud Uploads (10 Users)")
    start = time.perf_counter()

    async def upload_resume_for_user(user_token_obj):
        idx = user_token_obj["idx"]
        token = user_token_obj["token"]
        headers = {"Authorization": f"Bearer {token}"}
        filename = f"candidate_resume_{RUN_ID}_{idx}.pdf"
        files = {"file": (filename, io.BytesIO(VALID_PDF_BYTES), "application/pdf")}
        res = await client.post("/resumes/upload", headers=headers, files=files)
        return idx, res

    tasks = [upload_resume_for_user(u) for u in user_tokens]
    results = await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start

    success_count = 0
    for idx, res in results:
        if res.status_code == 201:
            data = res.json()
            success_count += 1
            user_resume_ids[idx] = data["id"]
        else:
            print(f"  [X] User {idx} cloud upload failed: {res.status_code} - {res.text}")

    status = "PASSED" if success_count == 10 else "FAILED"
    print(f"  Result: {success_count}/10 valid PDF uploads to Supabase in {elapsed:.3f}s -> {status}")
    test_results["Scenario G (Concurrent Cloud Storage Uploads)"] = {
        "status": status,
        "detail": f"{success_count}/10 PDFs uploaded concurrently to Supabase Storage in {elapsed:.3f}s",
    }


async def test_scenario_h_resume_ownership_and_deletion(client: httpx.AsyncClient):
    """Scenario H: Verify unauthorized delete is blocked, then delete own resumes concurrently."""
    print_header("SCENARIO H: Resume Ownership Check & Concurrent Cloud Deletion")
    user1 = user_tokens[0]
    user2 = user_tokens[1]

    u1_resume_id = user_resume_ids.get(user1["idx"])
    u2_headers = {"Authorization": f"Bearer {user2['token']}"}

    # 1. User 2 attempts to delete User 1's resume
    tamper_res = await client.delete(f"/resumes/{u1_resume_id}", headers=u2_headers)
    tamper_blocked = tamper_res.status_code in (403, 404)
    print(f"  User 2 unauthorized DELETE of User 1 Resume: Status {tamper_res.status_code} (Expected 404/403)")

    # 2. Concurrently delete all 10 resumes
    start = time.perf_counter()

    async def delete_own_resume(user_token_obj):
        idx = user_token_obj["idx"]
        token = user_token_obj["token"]
        resume_id = user_resume_ids[idx]
        headers = {"Authorization": f"Bearer {token}"}
        res = await client.delete(f"/resumes/{resume_id}", headers=headers)
        return idx, res.status_code

    tasks = [delete_own_resume(u) for u in user_tokens]
    del_results = await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start

    del_success = sum(1 for _, code in del_results if code == 200)
    passed = tamper_blocked and del_success == 10
    status = "PASSED" if passed else "FAILED"

    print(f"  Concurrent authorized deletions: {del_success}/10 successful in {elapsed:.3f}s")
    print(f"  Result -> {status}")
    test_results["Scenario H (Ownership & Cloud Deletion)"] = {
        "status": status,
        "detail": f"Unauthorized delete blocked ({tamper_res.status_code}); 10/10 resumes deleted from cloud & DB in {elapsed:.3f}s",
    }


async def run_all():
    print("=" * 70)
    print(f"  AI ATS BACKEND QA AUTOMATION SUITE — RUN ID: {RUN_ID}")
    print(f"  Testing Target: {BASE_URL}")
    print("=" * 70)

    # 60s timeout for network/cloud storage roundtrips
    limits = httpx.Limits(max_connections=50, max_keepalive_connections=20)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0, limits=limits) as client:
        await test_scenario_a_concurrency_register(client)
        await test_scenario_b_race_condition(client)
        await test_scenario_c_concurrent_login(client)
        await test_scenario_d_profile_creation(client)
        await test_scenario_e_ownership_security(client)
        await test_scenario_f_invalid_file_validation(client)
        await test_scenario_g_concurrent_resume_uploads(client)
        await test_scenario_h_resume_ownership_and_deletion(client)

    print_header("FINAL TEST SUITE SUMMARY")
    all_passed = True
    for scenario, res in test_results.items():
        print(f"  [{res['status']}] {scenario}: {res['detail']}")
        if res["status"] != "PASSED":
            all_passed = False

    overall = "PASSED (100%)" if all_passed else "FAILED"
    print("\n" + "=" * 70)
    print(f"  OVERALL RESULT: {overall}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_all())
