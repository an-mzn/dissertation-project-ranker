// Paste this entire file into the console on the university project-list page.
// Exports only title, supervisor, and the full description to projects.csv.
(async () => {
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  const rows = [...document.querySelectorAll('tr[onclick*="showProjectDetails("]')];
  console.log(`Found ${rows.length} project rows on this page.`);
  if (!rows.length) {
    console.warn("No matching rows. Open the project-list page; this script requires the original university page layout.");
    return;
  }

  const fields = {
    "Project title": "title",
    "Project supervisor": "supervisor",
    "Project description": "description"
  };
  const projects = [];
  const failed = [];
  const readDetails = () => {
    const tbody = [...document.querySelectorAll("tbody")].find(table =>
      [...table.rows].some(row => row.cells[0]?.textContent.trim() === "Project description:")
    );
    if (!tbody) return null;
    const result = {};
    for (const row of tbody.rows) {
      if (row.cells.length < 2) continue;
      const key = row.cells[0].textContent.trim().replace(/:$/, "");
      if (!Object.prototype.hasOwnProperty.call(fields, key)) continue;
      result[fields[key]] = (row.cells[1].innerText || row.cells[1].textContent).trim();
    }
    return result;
  };

  const waitForProject = async (title, supervisor) => {
    const start = Date.now();
    while (Date.now() - start < 12000) {
      const data = readDetails();
      if (data?.title === title && data?.supervisor === supervisor && data?.description !== undefined) {
        return data;
      }
      await sleep(150);
    }
    throw new Error(`Timed out: ${title}`);
  };

  const closePopup = () => {
    const close = [...document.querySelectorAll("a")].find(link =>
      link.textContent.trim() === "Close" &&
      link.getAttribute("onclick")?.includes("windowPopupDivView")
    );
    if (close) close.click();
  };

  for (let index = 0; index < rows.length; index++) {
    const row = rows[index];
    const title = row.cells[2]?.textContent.trim();
    const supervisor = row.cells[0]?.textContent.trim();
    try {
      if (!title || !supervisor) throw new Error(`Missing title or supervisor in row ${index + 1}.`);
      row.click();
      projects.push(await waitForProject(title, supervisor));
      console.log(`✓ ${index + 1}/${rows.length}: ${title}`);
    } catch (error) {
      failed.push({title, supervisor, error: error.message});
      console.warn(error.message);
    } finally {
      closePopup();
    }
    await sleep(250);
  }

  const columns = ["title", "supervisor", "description"];
  const escapeCSV = value => `"${String(value ?? "").replace(/"/g, '""')}"`;
  const csv = [
    columns.map(escapeCSV).join(","),
    ...projects.map(project => columns.map(column => escapeCSV(project[column])).join(","))
  ].join("\r\n");

  if (projects.length) {
    const blob = new Blob(["\uFEFF", csv], {type: "text/csv;charset=utf-8"});
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "projects.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  }
  console.log(`COMPLETE — extracted ${projects.length}/${rows.length}.`);
  if (failed.length) console.warn("Export is incomplete. Failed projects:", failed);
})();
