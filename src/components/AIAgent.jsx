import React, { useEffect, useMemo, useState } from "react";
/* import Navbar from "./Navbar";
import Footer from "./HomeFooter"; */

// const API_BASE = (import.meta.env.VITE_API_BASE||"http://localhost:8000") + "/api";
const API_BASE = "/api";

const defaultHashtags = ["#G-TechRising", "#PlantHerTechFuture", "#RuralWomenInTech"]; 

function AIAgent() {
	const [tab, setTab] = useState("news");
	const [loading, setLoading] = useState(false);
	const [items, setItems] = useState([]);
	const [selected, setSelected] = useState(null);
	const [form, setForm] = useState({ title: "", summary: "", url: "", image: "", hashtags: defaultHashtags.join(" ") });
	const [message, setMessage] = useState("");

	const demoData = useMemo(() => ({
		news: [
			{ type: "news", title: "African fintech raises new funding", summary: "A Nairobi-based fintech announced a seed extension to scale inclusive payments.", url: "https://example.com/africa-fintech", image: "https://placehold.co/600x320?text=Fintech", hashtags: defaultHashtags },
			{ type: "news", title: "Egypt startup expands cloud services", summary: "Cairo startup launches regional cloud platform targeting SMEs across North Africa.", url: "https://example.com/egypt-cloud", image: "https://placehold.co/600x320?text=Cloud", hashtags: defaultHashtags }
		],
		success: [
			{ type: "success", title: "Female-founded healthtech hits profitability", summary: "Lagos healthtech reaches profitability after expanding to rural clinics.", url: "https://example.com/healthtech", image: "https://placehold.co/600x320?text=Healthtech", hashtags: defaultHashtags }
		],
		events: [
			{ type: "event", title: "Africa Tech Summit (Virtual, Free)", summary: "Join thought leaders discussing AI adoption across the continent.", url: "https://example.com/ats-virtual", image: "https://placehold.co/600x320?text=Summit", hashtags: defaultHashtags },
			{ type: "event", title: "Women in Tech Africa Meetup — Accra", summary: "Community meetup focused on career pathways and mentorship.", url: "https://example.com/wita-accra", image: "https://placehold.co/600x320?text=Meetup", hashtags: defaultHashtags }
		]
	}), []);

	const fetchItems = async (kind) => {
		setLoading(true);
		setMessage("");
		try {
			const res = await fetch(`${API_BASE}/ai/generate/?type=${kind}`);
			const data = await res.json();
			if (res.ok) {
				setItems(data.items || []);
			} else {
				setItems(demoData[kind] || []);
				setMessage("Loaded demo data (backend unavailable)");
			}
		} catch (e) {
			setItems(demoData[kind] || []);
			setMessage("Loaded demo data (backend unavailable)");
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => { fetchItems(tab); }, [tab]);

	const onSelect = (it) => {
		setSelected(it);
		setForm({
			title: it.title || "",
			summary: it.summary || "",
			url: it.url || "",
			image: it.image || "",
			hashtags: (it.hashtags || defaultHashtags).join(" ")
		});
	};

	const updateField = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

	const shareLinkedIn = async () => {
		setMessage("");
		try {
			const res = await fetch(`${API_BASE}/social/linkedin/`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					text: `${form.title}\n\n${form.summary}${form.image ? `\n\nImage: ${form.image}`: ''}`.slice(0, 1100),
					url: form.url,
					image: form.image,
					hashtags: form.hashtags.split(/\s+/).filter(Boolean)
				})
			});
			const data = await res.json();
			if (!res.ok) throw new Error(data.error || "LinkedIn post failed");
			setMessage("Shared to LinkedIn");
		} catch (e) {
			setMessage(e.message || "LinkedIn share unavailable in demo mode");
		}
	};

	const shareInstagram = async () => {
		setMessage("");
		try {
			const res = await fetch(`${API_BASE}/social/instagram/`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					text: `${form.title}\n\n${form.summary}`.slice(0, 1900),
					image: form.image,
					hashtags: form.hashtags.split(/\s+/).filter(Boolean)
				})
			});
			const data = await res.json();
			if (!res.ok) throw new Error(data.error || "Instagram post failed");
			setMessage("Shared to Instagram");
		} catch (e) {
			setMessage(e.message || "Instagram share unavailable in demo mode");
		}
	};

	return (
		<div className="container py-4">
			{/* <Navbar /> */}
			<h2 className="mb-3">AI Tech Content Agent</h2>
			<div className="btn-group mb-3">
				<button className={`btn btn-outline-primary ${tab==='news'?'active':''}`} onClick={() => setTab('news')}>Tech News</button>
				<button className={`btn btn-outline-primary ${tab==='events'?'active':''}`} onClick={() => setTab('events')}>Tech Events</button>
				<button className={`btn btn-outline-primary ${tab==='success'?'active':''}`} onClick={() => setTab('success')}>Success Stories</button>
			</div>
			{loading && <div>Loading...</div>}
			{message && <div className="alert alert-info">{message}</div>}
			<div className="row">
				<div className="col-md-7">
					<div className="list-group">
						{items.map((it, idx) => (
							<button key={idx} className={`list-group-item list-group-item-action ${selected===it? 'active':''}`} onClick={() => onSelect(it)}>
								<div className="d-flex w-100 justify-content-between">
									<h5 className="mb-1">{it.title}</h5>
									<small>{it.type}</small>
								</div>
								{it.image && <img alt="preview" src={it.image} style={{maxWidth:'100%', borderRadius:6, marginTop:6}} />}
								<p className="mb-1 mt-2">{it.summary}</p>
								<small>{it.url}</small>
							</button>
						))}
					</div>
				</div>
				<div className="col-md-5">
					<div className="card">
						<div className="card-body">
							<h5 className="card-title">Edit & Approve</h5>
							{form.image && <img alt="selected" src={form.image} style={{maxWidth:'100%', borderRadius:6, marginBottom:10}} />}
							<input className="form-control mb-2" placeholder="Title" value={form.title} onChange={updateField('title')} />
							<textarea className="form-control mb-2" rows={6} placeholder="Summary" value={form.summary} onChange={updateField('summary')} />
							<input className="form-control mb-2" placeholder="URL" value={form.url} onChange={updateField('url')} />
							<input className="form-control mb-2" placeholder="Image URL" value={form.image} onChange={updateField('image')} />
							<input className="form-control mb-2" placeholder="Hashtags" value={form.hashtags} onChange={updateField('hashtags')} />
							<div className="d-flex gap-2 mt-2">
								<button className="btn btn-primary" onClick={shareLinkedIn}>Share to LinkedIn</button>
								<button className="btn btn-danger" onClick={shareInstagram}>Share to Instagram</button>
							</div>
						</div>
					</div>
				</div>
			</div>
			{/* <Footer /> */}
		</div>
	);
}

export default AIAgent;
