"""Test DOM extraction with realistic Indeed HTML"""

import asyncio
import sys
import os
from playwright.async_api import async_playwright

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scraper.adapters.indeed import IndeedAdapter


# Sample Indeed HTML with actual structure
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<body>
<div id="mosaic-provider-jobcards">
  <div>
    <ul>
      <li class="css-1ac2h1w eu4oa1w0"><!--$--><div class="cardOutline tapItem dd-privacy-allow result job_9b6b90751b656a90 resultWithShelf sponTapItem desktop css-1n3pb8f eu4oa1w0"><div class="slider_container css-weo834 eu4oa1w0" data-testid="slider_container"><div class="slider_list css-1bej0z4 eu4oa1w0"><div data-testid="slider_item" class="slider_item css-17bghu4 eu4oa1w0"><div data-testid="fade-in-wrapper" class="css-u74ql7 eu4oa1w0"><div class="job_seen_beacon"><table class="mainContentTable css-131ju4w eu4oa1w0" cellpadding="0" cellspacing="0" role="presentation"><tbody><tr><td class="resultContent css-1o6lhys eu4oa1w0"><div class="css-pt3vth e37uo190"><h2 class="jobTitle css-1o1rnx9 eu4oa1w0" tabindex="-1"><a id="job_9b6b90751b656a90" data-mobtk="1jh0s9vlghn3i86t" data-jk="9b6b90751b656a90" data-hiring-event="false" data-hide-spinner="true" role="button" aria-label="full details of Sales Advisor-Part Time" class="jcs-JobTitle css-1baag51 eu4oa1w0" href="/rc/clk?jk=9b6b90751b656a90&amp;bb=iZ5_JkklFNgZNycP-9k-Oh0BOaqzGJRH_4s1cQO1gMy3jyB_8bgnmaZJ0uPBEFnvZqhNTrLSMxbB_moy5uqnKS8XHs7viPnGrJMvAYzAAwq5XFIqcgZEhWz4JmybKh1_&amp;xkcb=SoAi67M3ngwoIPAfK70LbzkdCdPP&amp;fccid=7c13ea7d2941e927&amp;vjs=3"><span title="Sales Advisor-Part Time" id="jobTitle-9b6b90751b656a90">Sales Advisor-Part Time</span></a></h2><div class="css-j160pq e37uo190"><div class="mosaic-provider-jobcards-1uo542s e1xnxm2i0"><div class="mosaic-provider-jobcards-1oa1vqn ecydgvn0"><div class="mosaic-provider-jobcards-1f1q1js ecydgvn1">Often responds within 3 days</div></div></div></div></div><div class="css-u74ql7 eu4oa1w0"><div class="company_location css-1k93hyy e37uo190"><div elementtiming="significant-render" data-testid="timing-attribute"><div class="css-1afmp4o e37uo190"><span data-testid="company-name" class="css-19eicqx eu4oa1w0">H&amp;M</span></div><div data-testid="text-location" class="css-1f06pz4 eu4oa1w0">Gurugram, Haryana</div></div></div><div class="jobMetaDataGroup css-jf723e eu4oa1w0"><ul class="heading6 tapItem-gutter metadataContainer css-1hl5lcb eu4oa1w0"><li class="mosaic-provider-jobcards-fswglz e1xnxm2i0" data-testid="attribute_snippet_testid"><div class="mosaic-provider-jobcards-1oa1vqn ecydgvn0"><div class="mosaic-provider-jobcards-1f1q1js ecydgvn1"><span class="css-zydy3i e1wnkr790">Part-time</span></div></div></li><li class="mosaic-provider-jobcards-fswglz e1xnxm2i0"><div class="mosaic-provider-jobcards-1oa1vqn ecydgvn0"><div class="mosaic-provider-jobcards-1f1q1js ecydgvn1"><span class="css-zydy3i e1wnkr790">Health insurance</span></div></div></li></ul><div class="heading6 error-text tapItem-gutter"></div></div><div role="presentation" class="css-r19t1s eu4oa1w0"><div class="css-6stls4 eu4oa1w0"><span class="iaIcon css-1f0h0ey e1wnkr790"><svg xmlns="http://www.w3.org/2000/svg" focusable="false" role="img" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true" class="mosaic-provider-jobcards-ptur8y eac13zx0"><path d="M4.406 19.533a1.103 1.103 0 01-1.082-.097c-.34-.221-.51-.54-.51-.954v-4.314L11.09 12 2.815 9.833V5.518c0-.414.17-.732.51-.954.34-.222.7-.254 1.08-.096l15.341 6.482c.469.207.703.557.703 1.05s-.234.844-.703 1.05l-15.34 6.483z"></path></svg><span data-testid="indeedApply">Easily apply</span></span></div><div class="underShelfFooter"><div class="heading6 tapItem-gutter css-1wcu7u6 eu4oa1w0"></div></div></div></div></td></tr></tbody></table><a rel="nofollow" class="more_loc css-660mcl eu4oa1w0" href="/addlLoc/redirect?tk=1jh0s9vlghn3i86t&amp;jk=9b6b90751b656a90&amp;dest=%2Fjobs%3Fq%3D%26l%3DGurugram%252C%2BHaryana%26radius%3D25%26grpKey%3D8gcFdG5mZWy4D9xfqhAaCglub3JtdGl0bGUaDXNhbGVzIGFkdmlzb3I%253D" aria-label="View similar jobs with this employer" data-testid="location-rollup">View similar jobs with this employer</a><div class="ctaContainer ctaContainer_withCompanyInfo"><button class="bookmark bookmark-tap-target mosaic-provider-jobcards-ykqx5t e8ju0x50" aria-label="Save job Toggle" aria-pressed="false"><svg xmlns="http://www.w3.org/2000/svg" focusable="false" role="presentation" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true" class="mosaic-provider-jobcards-s0xhw4 eac13zx0"><path d="M12 18.221l-4.027 1.723c-.758.319-1.477.256-2.157-.19-.68-.446-1.02-1.077-1.02-1.892V5.072c0-.63.222-1.166.666-1.61.443-.443.98-.665 1.61-.665h9.856c.63 0 1.166.222 1.61.665.443.444.665.98.665 1.61v12.79c0 .815-.34 1.446-1.02 1.892-.679.445-1.398.509-2.156.19L12 18.22zm0-2.493l4.928 2.115V5.072H7.072v12.77L12 15.729z"></path></svg></button></div><div aria-live="polite"></div></div></div></div><div data-testid="slider_sub_item" class="slider_sub_item css-u74ql7 eu4oa1w0"><div data-testid="belowJobSnippet" class="css-1vlebyu eu4oa1w0"><ul style="list-style-type:circle;margin-top: 0px;margin-bottom: 0px;padding-left:20px;">
 <li style="margin-bottom:0px;">As a Sales Advisor Part Time at H&amp;M, you’ll play a key role in creating an outstanding customer experience.</li>
 <li>Collaborate with your team to deliver exceptional…</li>
</ul></div><div class="css-1a1rhwu eu4oa1w0"><div class="result-tab visible css-1243kpv eu4oa1w0"><div data-testid="more_links" class="css-1b45w5d eu4oa1w0"><ul><li><span class="mat">View all <a href="/q-h&amp;m-jobs.html" class="css-1k2hae4 e19afand0">H&amp;M jobs</a></span></li><li><span class="mat">Salary Search: <a href="/career/sales-advisor/salaries/Gurugram--Haryana?campaignid=serp-more&amp;fromjk=9b6b90751b656a90&amp;from=serp-more" class="css-1k2hae4 e19afand0">Sales Advisor-Part Time salaries in Gurugram, Haryana</a></span></li><li><span class="mat">See popular <a href="/cmp/H&amp;M/faq" class="css-1k2hae4 e19afand0">questions &amp; answers about H&amp;M</a></span></li></ul></div></div></div></div></div></div></div><span aria-live="polite" class="visually-hidden css-16euvrx eu4oa1w0"></span><!--/$--></li>
      <li class="css-1ac2h1w eu4oa1w0">
        <div class="cardOutline">
          <table>
            <tr>
              <td>
                <h2 class="jobTitle">
                  <a data-jk="abc123def456" 
                     href="/viewjob?jk=abc123def456">
                    <span title="Software Engineer">Software Engineer</span>
                  </a>
                </h2>
                <div class="company_location">
                  <span data-testid="company-name">Tech Corp</span>
                  <div data-testid="text-location">Bangalore, Karnataka</div>
                </div>
              </td>
            </tr>
          </table>
        </div>
      </li>
    </ul>
  </div>
</div>
</body>
</html>
"""


async def test_dom_extraction():
    """Test that _extract_jobs_from_dom correctly parses job cards"""
    print("Testing DOM extraction with realistic Indeed HTML...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Load sample HTML
        await page.set_content(SAMPLE_HTML)

        # Create adapter
        adapter = IndeedAdapter(context=None)

        # Extract jobs
        jobs = await adapter._extract_jobs_from_dom(page)

        print(f"\n✓ Extracted {len(jobs)} jobs")
        print("=" * 60)

        for i, job in enumerate(jobs, 1):
            print(f"\nJob {i}:")
            print(f"  ID: {job.get('id', 'MISSING')}")
            print(f"  Title: {job.get('title', 'MISSING')}")
            print(f"  Company: {job.get('company', 'MISSING')}")
            print(f"  Location: {job.get('location', 'MISSING')}")
            print(f"  URL: {job.get('url', 'MISSING')}")

        print("\n" + "=" * 60)

        # Verify expectations
        assert len(jobs) == 2, f"Expected 2 jobs, got {len(jobs)}"

        # Check first job
        job1 = jobs[0]
        assert job1["id"] == "9b6b90751b656a90", "Job 1 ID mismatch"
        assert job1["title"] == "Sales Advisor-Part Time", "Job 1 title mismatch"
        assert job1["company"] == "H&M", "Job 1 company mismatch"
        assert job1["location"] == "Gurugram, Haryana", "Job 1 location mismatch"
        assert "/rc/clk?jk=9b6b90751b656a90" in job1["url"], "Job 1 URL mismatch"

        # Check second job
        job2 = jobs[1]
        assert job2["id"] == "abc123def456", "Job 2 ID mismatch"
        assert job2["title"] == "Software Engineer", "Job 2 title mismatch"
        assert job2["company"] == "Tech Corp", "Job 2 company mismatch"
        assert job2["location"] == "Bangalore, Karnataka", "Job 2 location mismatch"

        print("\n✅ All assertions passed!")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_dom_extraction())
