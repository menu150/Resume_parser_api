import styles from "./index.module.css";

export default function Home() {
  return (
    <section className={styles.wrapper}>
      <h1 className={styles.title}>ResumeParse Dashboard</h1>
      <div className={styles.grid}>
        <StatCard title="Uploads Today" value="14" />
        <StatCard title="Active API Keys" value="3" />
        <StatCard title="Quota Remaining" value="86 / 100" />
      </div>
    </section>
  );
}

function StatCard({ title, value }: { title: string; value: string }) {
  return (
    <div className={styles.card}>
      <p className={styles.cardTitle}>{title}</p>
      <p className={styles.cardValue}>{value}</p>
    </div>
  );
}
